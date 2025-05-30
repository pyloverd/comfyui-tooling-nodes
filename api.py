from __future__ import annotations
from aiohttp import web
from typing import NamedTuple
from pathlib import Path
import json
import traceback
import re
import logging

from comfy import model_detection
import comfy.utils
import folder_paths
import server

from .translation import available_languages, translate
from .krita import WorkflowExchange

input_block_name = "model.diffusion_model.input_blocks.0.0.weight"

model_names = {
    "SD15": "sd15",
    "SD20": "sd20",
    "SD21UnclipL": "sd21",
    "SD21UnclipH": "sd21",
    "SDXLRefiner": "sdxl-refiner",
    "SDXL": "sdxl",
    "SSD1B": "ssd1b",
    "SVD_img2vid": "svd",
    "Stable_Cascade_B": "cascade-b",
    "Stable_Cascade_C": "cascade-c",
    "SD3": "sd3",
    "AuraFlow": "aura-flow",
    "HunyuanDiT": "hunyuan-dit",
    "HunyuanDiT1": "hunyuan-dit",
    "Flux": "flux",
    "FluxInpaint": "flux",
    "FluxSchnell": "flux-schnell",
    "GenmoMochi": "mochi",
    "LTXV": "ltxv",
    "HunyuanVideo": "hunyuan-video",
    "Lumina2": "lumina2",
}

gguf_architectures = {"sd1": "sd15"}


class FakeTensor(NamedTuple):
    shape: tuple

    @staticmethod
    def from_dict(d):
        try:
            return FakeTensor(tuple(d["shape"]))
        except KeyError:
            return d


def inspect_safetensors(filename: str, model_type: str, is_checkpoint: bool):
    try:
        # Read header of safetensors file
        path = folder_paths.get_full_path(model_type, filename)
        header = comfy.utils.safetensors_header(path)
        if header:
            cfg = json.loads(header.decode("utf-8"))

            # Build a fake "state_dict" from the header info to avoid reading the full weights
            for key in cfg:
                if not key == "__metadata__":
                    cfg[key] = FakeTensor.from_dict(cfg[key])

            # Reuse Comfy's model detection
            prefix = model_detection.unet_prefix_from_state_dict(cfg)
            if not is_checkpoint:
                cfg = comfy.utils.state_dict_prefix_replace(cfg, {prefix: ""}, filter_keys=False)
                prefix = ""
            try:  # latest ComfyUI takes 2 args
                unet_config = model_detection.detect_unet_config(cfg, prefix)
            except TypeError as e:  # older ComfyUI versions take 3 args
                raise TypeError(f"{e} when calling detect_unet_config - old version of ComfyUI?")

            # Get input count to detect inpaint models
            if input_block := cfg.get(input_block_name, None):
                input_count = input_block.shape[1]
            else:
                input_count = 4

            # Find a matching base model depending on unet config
            base_model = model_detection.model_config_from_unet_config(unet_config)
            if base_model is None:
                return {"base_model": "unknown"}

            base_model_class = base_model.__class__
            base_model_name = model_names.get(base_model_class.__name__, "unknown")
            result = {"base_model": base_model_name}
            result["is_inpaint"] = (
                base_model_name in ["sd15", "sdxl"] and input_count > 4
            ) or base_model_class.__name__ == "FluxInpaint"
            if base_model_name == "sdxl":
                result["type"] = base_model.model_type(cfg).name.lower().replace("_", "-")
            return result
        return {"base_model": "unknown"}
    except Exception as e:
        # traceback.print_exc()
        return {"base_model": "unknown", "error": f"Failed to detect base model: {e}"}


def inspect_gguf(filename: str, model_type: str):
    try:
        import gguf
    except ImportError:
        return {"base_model": "unknown", "error": "GGUF module not found"}

    try:
        path = folder_paths.get_full_path(model_type, filename)
        reader = gguf.GGUFReader(path)
        arch_field = reader.get_field("general.architecture")
        if arch_field is not None:
            if len(arch_field.types) != 1 or arch_field.types[0] != gguf.GGUFValueType.STRING:
                raise TypeError(
                    f"Bad type for GGUF general.architecture key: expected string, got {arch_field.types!r}"
                )
            arch_str = str(arch_field.parts[arch_field.data[-1]], encoding="utf-8")
        else:  # stable-diffusion.cpp, requires conversion. not handled for now
            return {"base_model": "flux", "is_inpaint": False}
        return {
            "base_model": gguf_architectures.get(arch_str, arch_str),
            "is_inpaint": False,
        }
    except Exception as e:
        # traceback.print_exc()
        return {"base_model": "unknown", "error": f"Failed to detect base model: {e}"}


def inspect_diffusion_model(filename: str, model_type: str, is_checkpoint: bool):
    if filename.endswith(".gguf"):
        return inspect_gguf(filename, model_type)
    return inspect_safetensors(filename, model_type, is_checkpoint)


def inspect_models(model_type: str):
    try:
        try:
            files = folder_paths.get_filename_list(model_type)
        except KeyError:
            return web.json_response({"error": f"Model folder not found: {model_type}"})
        is_checkpoint = model_type == "checkpoints"
        info = {
            filename: inspect_diffusion_model(filename, model_type, is_checkpoint)
            for filename in files
        }
        return web.json_response(info)
    except Exception as e:
        traceback.print_exc()
        return web.json_response(dict(error=str(e)), status=500)


def has_invalid_folder_name(folder_name: str):
    valid_names = list(folder_paths.folder_names_and_paths.keys())
    if folder_name not in valid_names:
        return web.json_response(
            dict(error=f"Invalid folder path, must be one of {', '.join(valid_names)}"),
            status=400,
        )
    return None


def has_invalid_filename(filename: str):
    if not filename.lower().endswith((".sft", ".safetensors")):
        return web.json_response(dict(error="File extension must be .safetensors"), status=400)
    if not filename or not filename.strip() or len(filename) > 255:
        return web.json_response(dict(error="Invalid filename"), status=400)
    if any(char in filename for char in ["..", "/", "\\", "\n", "\r", "\t", "\0"]):
        return web.json_response(dict(error="Invalid filename"), status=400)
    if filename.startswith(".") or not re.match(r"^[a-zA-Z0-9_\-. ]+$", filename):
        return web.json_response(dict(error="Invalid filename"), status=400)
    return None


_server: server.PromptServer | None = getattr(server.PromptServer, "instance", None)
if _server is not None:
    _workflow_exchange = WorkflowExchange(_server)

    @_server.routes.get("/api/etn/model_info/{folder_name}")
    async def model_info(request: web.Request):
        folder_name = request.match_info.get("folder_name", "checkpoints")
        error = has_invalid_folder_name(folder_name)
        if error is not None:
            return error
        return inspect_models(folder_name)

    @_server.routes.get("/api/etn/model_info")
    async def api_model_info(request):
        return inspect_models("checkpoints")

    @_server.routes.get("/api/etn/languages")
    async def languages(request):
        try:
            result = [dict(name=name, code=code) for code, name in available_languages()]
            return web.json_response(result)
        except Exception as e:
            return web.json_response(dict(error=str(e)), status=500)

    @_server.routes.get("/api/etn/translate/{lang}/{text}")
    async def translate_text(request):
        try:
            language = request.match_info.get("lang", "en")
            text = request.match_info.get("text", "")
            result = translate(f"lang:{language} {text}")
            return web.json_response(result)
        except Exception as e:
            return web.json_response(dict(error=str(e)), status=500)

    @_server.routes.put("/api/etn/upload/{folder_name}/{filename}")
    async def upload(request: web.Request):
        folder_name = request.match_info.get("folder_name", "")
        error = has_invalid_folder_name(folder_name)
        if error is not None:
            return error

        filename = request.match_info.get("filename", "")
        error = has_invalid_filename(filename)
        if error is not None:
            return error

        try:
            if folder_paths.get_full_path(folder_name, filename) is not None:
                return web.json_response(dict(status="cached"), status=200)

            folder = Path(folder_paths.folder_names_and_paths[folder_name][0][0])
            total_size = int(request.headers.get("Content-Length", "0"))
            logging.info(
                f"Uploading {filename} ({total_size / (1024**2):.1f} MB) to {folder} folder"
            )

            with open(folder / filename, "wb") as f:
                async for chunk, _ in request.content.iter_chunks():
                    f.write(chunk)

            return web.json_response(dict(status="success"), status=201)
        except Exception as e:
            return web.json_response(dict(error=str(e)), status=500)

    async def _handle_workflow_request(request: web.Request, handler, *arg_keys):
        try:
            data = await request.json()
            args = [data[key] for key in arg_keys]
            await handler(*args)
            return web.json_response(dict(status="success"), status=200)
        except KeyError as e:
            return web.json_response(dict(error=str(e)), status=400)
        except Exception as e:
            return web.json_response(dict(error=str(e)), status=500)

    @_server.routes.post("/api/etn/workflow/publish")
    async def publish_workflow(request: web.Request):
        return await _handle_workflow_request(
            request, _workflow_exchange.publish, "name", "client_id", "workflow"
        )

    @_server.routes.post("/api/etn/workflow/subscribe")
    async def subscribe_workflow(request: web.Request):
        return await _handle_workflow_request(request, _workflow_exchange.subscribe, "client_id")

    @_server.routes.post("/api/etn/workflow/unsubscribe")
    async def unsubscribe_workflow(request: web.Request):
        return await _handle_workflow_request(request, _workflow_exchange.unsubscribe, "client_id")
