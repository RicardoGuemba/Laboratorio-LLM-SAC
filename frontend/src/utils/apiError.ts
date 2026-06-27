export function parseApiError(detail: unknown, fallback: string): string {
  if (typeof detail === "string") {
    if (detail === "Method Not Allowed") {
      return "Servidor desatualizado. Feche o app e abra novamente para atualizar.";
    }
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: string }).msg);
        }
        return "";
      })
      .filter(Boolean)
      .join("; ");
  }
  return fallback;
}

export async function readApiError(res: Response, fallback: string): Promise<string> {
  try {
    const err = await res.json();
    return parseApiError(err.detail, fallback);
  } catch {
    return fallback;
  }
}
