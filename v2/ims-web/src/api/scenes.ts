import registry from "./file-scenes.json";

export interface FileScene {
  exts: string[];
  maxBytes: number;
  maxMb: number;
  watermark: boolean;
}

const scenes = registry as Record<string, FileScene>;

export function fileScene(code: string): FileScene | undefined {
  return scenes[code];
}

export function sceneAccept(code: string): string {
  const scene = scenes[code];
  if (!scene) return "";
  return scene.exts.map((ext) => `.${ext}`).join(",");
}

export function validateFile(code: string, file: File): string | null {
  const scene = scenes[code];
  if (!scene) return "不支持的上传场景";
  const ext = file.name.includes(".") ? file.name.split(".").pop()!.toLowerCase() : "";
  if (!scene.exts.includes(ext)) {
    return `仅支持 ${scene.exts.join("、")} 格式`;
  }
  if (file.size > scene.maxBytes) {
    return `文件不能超过 ${scene.maxMb} MB`;
  }
  return null;
}
