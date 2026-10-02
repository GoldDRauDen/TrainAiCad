import * as z from "zod/v4";
import {
  downloadUri,
  sniffKind,
  storeSource,
  type SourceRole,
} from "./ingest.js";
export const ChatGptFile = z
  .object({
    download_url: z.string().url(),
    file_id: z.string().min(1).max(256),
    mime_type: z.string().optional(),
    file_name: z.string().optional(),
  })
  .strict();
export type ChatGptFile = z.infer<typeof ChatGptFile>;
function fallbackName(bytes: Buffer, role: SourceRole): string {
  const kind = sniffKind(bytes);
  if (kind === "PDF") return "drawing.pdf";
  if (kind === "DXF") return role === "DRAWING" ? "drawing.dxf" : "data.dxf";
  if (bytes.subarray(0, 2).equals(Buffer.from([255, 216])))
    return "drawing.jpg";
  if (bytes.subarray(0, 4).toString() === "RIFF") return "drawing.webp";
  if (["II*\0", "MM\0*"].includes(bytes.subarray(0, 4).toString()))
    return "drawing.tif";
  if (bytes.subarray(0, 2).toString() === "BM") return "drawing.bmp";
  return "drawing.png";
}
/** Host file URLs are short-lived capabilities: never persist/log them or return them to the model. */
export async function ingestChatGptFile(
  file: ChatGptFile,
  role: SourceRole,
  download = downloadUri,
) {
  if (new URL(file.download_url).protocol !== "https:")
    throw new Error("CHATGPT_FILE_REQUIRES_HTTPS");
  const bytes = await download(file.download_url);
  const name = file.file_name || fallbackName(bytes, role);
  if (role === "DRAWING" && sniffKind(bytes) === "DXF")
    throw new Error("DRAWING_REQUIRES_PDF_OR_IMAGE");
  const stored = storeSource(
    { fileName: name, bytes, mimeType: file.mime_type },
    role,
  );
  return { stored, fileId: file.file_id };
}
