from __future__ import annotations

import random

from backend.config import load_config

FALLBACK_COMPLAINTS: dict[str, tuple[str, str]] = {
    "atraso_entrega": (
        "Atraso na entrega do pedido",
        "Comprei no site da TRUEPALEO há três semanas (pedido #TP-48291) e o prazo era de 7 dias úteis. "
        "O rastreio está parado e ninguém me dá retorno. Quero saber onde está meu Desodorante Natural.",
    ),
    "produto_defeituoso": (
        "Desodorante esfarela ao usar",
        "Recebi o Desodorante Natural TRUEPALEO e ele esfarela completamente na aplicação. "
        "Paguei R$ 58,90 e o produto parece seco demais. Pedido #TP-55102.",
    ),
    "reacao_alergica": (
        "Reação na pele após uso do kit",
        "Usei o kit com desodorante e balm por dois dias e tive vermelhidão e coceira. "
        "Suspendi o uso mas estou preocupada. Comprei pelo site oficial, pedido #TP-77341.",
    ),
    "sac_sem_resposta": (
        "SAC não responde meus e-mails",
        "Enviei três e-mails para o SAC da TRUEPALEO sobre meu pedido #TP-33408 e ninguém responde. "
        "O rastreio está parado há uma semana. Preciso de uma posição urgente.",
    ),
    "reembolso": (
        "Solicitação de reembolso do desodorante",
        "Comprei o Desodorante Natural, usei por 3 semanas conforme orientação e não funcionou. "
        "O site promete reembolso em 30 dias. Quero exercer essa garantia — pedido #TP-66789.",
    ),
    "produto_vencido": (
        "Tallow Balm recebido vencido",
        "Recebi meu Tallow Balm TRUEPALEO com validade vencida no rótulo. "
        "Não vou usar produto vencido na pele. Pedido #TP-33456, compra em maio.",
    ),
    "produto_nao_enviado": (
        "Pedido pago e não enviado",
        "Pagamento aprovado há 10 dias (pedido #TP-78102, Full Paleo Kit) e o status continua em separação. "
        "No site prometiam envio em 2 dias úteis. Cadê meu pedido?",
    ),
    "desodorante_ineficaz": (
        "Desodorante não funciona",
        "Usei o Desodorante Natural TRUEPALEO por um mês e continuo com odor. "
        "Li no site sobre garantia de eficácia. Quero reembolso — pedido #TP-88901.",
    ),
}


def fallback_complaint(category: str) -> tuple[str, str]:
    if category in FALLBACK_COMPLAINTS:
        return FALLBACK_COMPLAINTS[category]
    key = random.choice(list(FALLBACK_COMPLAINTS.keys()))
    return FALLBACK_COMPLAINTS[key]


def fallback_sac_response(complaint_title: str) -> str:
    return (
        f"Olá! Pedimos sinceras desculpas pelo transtorno relatado em \"{complaint_title}\". "
        "Para localizarmos seu pedido e resolvermos com agilidade, por favor confirme o número do pedido "
        "e o e-mail usado na compra. Nossa equipe retornará em até 24 horas úteis com uma solução concreta. "
        "Equipe TRUEPALEO."
    )
