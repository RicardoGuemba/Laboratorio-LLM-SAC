import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TicketThread } from "./TicketThread";

describe("TicketThread avatars", () => {
  it("shows manual complaint textarea in empty state", () => {
    render(
      <TicketThread
        sessionId={null}
        complaintTitle=""
        complaintText=""
        responseText=""
        liveComplaint=""
        liveResponse=""
        streamingRole={null}
      />,
    );
    expect(screen.getAllByRole("img")).toHaveLength(2);
    expect(screen.getByLabelText(/Reclamação manual/i)).toBeInTheDocument();
  });

  it("renders avatars beside complaint and response bubbles", () => {
    render(
      <TicketThread
        sessionId="abc-123-def"
        complaintTitle="Atraso na entrega"
        complaintText="Isso é um absurdo, não aguento mais esperar!"
        responseText="Pedimos sinceras desculpas pelo transtorno."
        liveComplaint=""
        liveResponse=""
        streamingRole={null}
        category="atraso_entrega"
      />,
    );
    const avatars = screen.getAllByRole("img");
    expect(avatars).toHaveLength(2);
    expect(avatars[0].getAttribute("aria-label")).toMatch(/frustrado/i);
    expect(avatars[1].getAttribute("aria-label")).toMatch(/empático/i);
  });

  it("sets speaking mood on active streaming role", () => {
    render(
      <TicketThread
        sessionId="abc-123"
        complaintTitle=""
        complaintText=""
        responseText=""
        liveComplaint="Gerando..."
        liveResponse=""
        streamingRole="cliente"
      />,
    );
    expect(screen.getAllByRole("img")[0].getAttribute("aria-label")).toMatch(/falando/i);
  });
});
