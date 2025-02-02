from . import api as api, nodes, tile, region, nsfw, translation, krita

NODE_CLASS_MAPPINGS = {
    "ETN_LoadImageBase64": nodes.LoadImageBase64,
    "ETN_LoadMaskBase64": nodes.LoadMaskBase64,
    "ETN_SendImageWebSocket": nodes.SendImageWebSocket,
    "ETN_CropImage": nodes.CropImage,
    "ETN_ApplyMaskToImage": nodes.ApplyMaskToImage,
    "ETN_ReferenceImage": nodes.ReferenceImage,
    "ETN_ApplyReferenceImages": nodes.ApplyReferenceImages,
    "ETN_TileLayout": tile.TileLayout,
    "ETN_ExtractImageTile": tile.ExtractImageTile,
    "ETN_ExtractMaskTile": tile.ExtractMaskTile,
    "ETN_GenerateTileMask": tile.GenerateTileMask,
    "ETN_MergeImageTile": tile.MergeImageTile,
    "ETN_BackgroundRegion": region.BackgroundRegion,
    "ETN_DefineRegion": region.DefineRegion,
    "ETN_ListRegionMasks": region.ListRegionMasks,
    "ETN_AttentionMask": region.AttentionMask,
    "ETN_NSFWFilter": nsfw.NSFWFilter,
    "ETN_Translate": translation.Translate,
    "ETN_KritaOutput": krita.KritaOutput,
    "ETN_KritaSendText": krita.KritaSendText,
    "ETN_KritaCanvas": krita.KritaCanvas,
    "ETN_KritaSelection": krita.KritaSelection,
    "ETN_KritaImageLayer": krita.KritaImageLayer,
    "ETN_KritaMaskLayer": krita.KritaMaskLayer,
    "ETN_Parameter": krita.Parameter,
    "ETN_KritaStyle": krita.KritaStyle,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "ETN_LoadImageBase64": "Load Image (Base64)",
    "ETN_LoadMaskBase64": "Load Mask (Base64)",
    "ETN_SendImageWebSocket": "Send Image (WebSocket)",
    "ETN_CropImage": "Crop Image",
    "ETN_ApplyMaskToImage": "Apply Mask to Image",
    "ETN_ReferenceImage": "Reference Image",
    "ETN_ApplyReferenceImages": "Apply Reference Images",
    "ETN_TileLayout": "Create Tile Layout",
    "ETN_ExtractImageTile": "Extract Image Tile",
    "ETN_ExtractMaskTile": "Extract Mask Tile",
    "ETN_MergeImageTile": "Merge Image Tile",
    "ETN_GenerateTileMask": "Generate Tile Mask",
    "ETN_BackgroundRegion": "Background Region",
    "ETN_DefineRegion": "Define Region",
    "ETN_ListRegionMasks": "List Region Masks",
    "ETN_AttentionMask": "Regions Attention Mask",
    "ETN_NSFWFilter": "NSFW Filter",
    "ETN_Translate": "Translate Text",
    "ETN_KritaOutput": "Krita Output",
    "ETN_KritaSendText": "Send Text",
    "ETN_KritaCanvas": "Krita Canvas",
    "ETN_KritaSelection": "Krita Selection",
    "ETN_KritaImageLayer": "Krita Image Layer",
    "ETN_KritaMaskLayer": "Krita Mask Layer",
    "ETN_Parameter": "Parameter",
    "ETN_KritaStyle": "Krita Style",
}
WEB_DIRECTORY = "./js"
