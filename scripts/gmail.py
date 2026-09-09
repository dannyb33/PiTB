import argparse
import base64
import json
import sys

from gmail_auth import gmail_authenticate
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from helper import clean_text, html_to_text

USER_ID = "me"
MAX_LIMIT = 500


def get_service():
    return build("gmail", "v1", credentials=gmail_authenticate())


def list_messages(service, limit: int) -> list[dict]:
    """Return the `limit` most recent messages as a list of {id, snippet}."""
    response = (
        service.users().messages().list(userId=USER_ID, maxResults=limit).execute()
    )
    refs = response.get("messages", [])

    entries = []
    for ref in refs:
        msg = (
            service.users()
            .messages()
            .get(userId=USER_ID, id=ref["id"], format="metadata")
            .execute()
        )
        entries.append(
            (
                int(msg.get("internalDate") or 0),  # newest first
                msg.get("id", ref["id"]),
                clean_text(msg.get("snippet", ""), single_line=True, unescape=True),
            )
        )

    entries.sort(reverse=True)
    return [
        {"id": message_id, "snippet": snippet} for _, message_id, snippet in entries
    ]


def get_message(service, message_id: str) -> dict:
    """Return the full email for `message_id`, with MIME bodies decoded."""
    message = (
        service.users()
        .messages()
        .get(userId=USER_ID, id=message_id, format="full")
        .execute()
    )
    payload = message.get("payload", {})

    text_parts: list[str] = []
    html_parts: list[str] = []

    def walk(part: dict) -> None:
        body = part.get("body", {})

        if body.get("data"):
            decoded = base64.urlsafe_b64decode(body["data"]).decode(
                "utf-8", errors="replace"
            )
            if part.get("mimeType") == "text/plain":
                text_parts.append(decoded)
            elif part.get("mimeType") == "text/html":
                html_parts.append(decoded)

        for child in part.get("parts") or []:
            walk(child)

    walk(payload)

    # Prefer the sender's plain-text part; convert HTML when there is none.
    if text_parts:
        text = "\n\n".join(text_parts)
    elif html_parts:
        text = html_to_text("\n".join(html_parts))
    else:
        text = ""

    email = {
        "id": message.get("id"),
        "snippet": clean_text(
            message.get("snippet", ""), single_line=True, unescape=True
        ),
        "text": clean_text(text),
    }
    return email


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gmail",
        description="Fetch messages from Gmail.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_cmd = subparsers.add_parser("list", help="List recent messages")
    list_cmd.add_argument(
        "-l",
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help=f"number of messages to list (default: 10, max: {MAX_LIMIT})",
    )

    get_cmd = subparsers.add_parser(
        "get",
        help="Fetch a single message in full",
    )
    get_cmd.add_argument(
        "id",
        help="message id to fetch in full",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        service = get_service()

        if args.command == "get":
            if args.id:
                result = get_message(service, args.id)
        elif args.command == "list":
            result = list_messages(service, args.limit)
    except HttpError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
