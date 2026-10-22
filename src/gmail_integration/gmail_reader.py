import base64
import logging

from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def get_gmail_service(creds):
    return build("gmail", "v1", credentials=creds)


def list_unread_messages(service, max_results=10):
    results = service.users().messages().list(
        userId="me", q="is:unread", maxResults=max_results
    ).execute()
    messages = results.get("messages", [])
    return [msg["id"] for msg in messages]


def get_message_raw(service, msg_id):
    """Devuelve los bytes crudos del mensaje (Gmail `format="raw"`).

    Args:
        service: cliente de la API de Gmail.
        msg_id: ID del mensaje.

    Returns:
        bytes crudos del mensaje (Base64 url-safe ya decodificado).
    """
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="raw"
    ).execute()
    return base64.urlsafe_b64decode(msg["raw"].encode("ASCII"))


def mark_as_read(service, msg_id):
    service.users().messages().modify(
        userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def move_to_label(service, msg_id, label_name="Phishing Alertas"):
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    label_id = None
    for lbl in labels:
        if lbl["name"] == label_name:
            label_id = lbl["id"]
            break

    if not label_id:
        label = service.users().labels().create(
            userId="me", body={"name": label_name}
        ).execute()
        label_id = label["id"]

    service.users().messages().modify(
        userId="me", id=msg_id,
        body={"addLabelIds": [label_id], "removeLabelIds": ["UNREAD"]}
    ).execute()
