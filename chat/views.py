
import json
import requests

from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Conversation, Message


@ensure_csrf_cookie
def home(request):
    if request.method == "GET":
        return render(request, "chat/index.html")

    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()
        conversation_id = request.POST.get("conversation_id")

        if not user_message:
            return JsonResponse(
                {"error": "Please enter a message."},
                status=400,
            )

        if conversation_id:
            conversation = get_object_or_404(
                Conversation,
                id=conversation_id
            )
        else:
            conversation = Conversation.objects.create(
                title=user_message[:50]
            )

        previous_messages = list(
            Message.objects.filter(
                conversation=conversation
            ).order_by("-created_at")[:10]
        )

        previous_messages.reverse()

        prompt = (
            "You are a helpful AI study assistant. "
            "Answer clearly and simply.\n\n"
        )

        for msg in previous_messages:
            if msg.role == "user":
                prompt += f"User: {msg.content}\n"
            else:
                prompt += f"Assistant: {msg.content}\n"

        prompt += f"User: {user_message}\nAssistant:"

        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_message,
        )

        def generate_response():
            full_reply = ""

            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3.2:1b",
                        "prompt": prompt,
                        "stream": True,
                    },
                    stream=True,
                    timeout=(10, 180),
                )

                response.raise_for_status()

                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        chunk = data.get("response", "")

                        if chunk:
                            full_reply += chunk
                            yield chunk

                        if data.get("done"):
                            break

                if full_reply.strip():
                    Message.objects.create(
                        conversation=conversation,
                        role="assistant",
                        content=full_reply,
                    )

            except requests.exceptions.RequestException as e:
                print("Ollama error:", repr(e))
                yield "\n[Error: Could not connect to Ollama.]"

            except Exception as e:
                print("Chatbot error:", repr(e))
                yield "\n[Error: Something went wrong.]"

        streaming_response = StreamingHttpResponse(
            generate_response(),
            content_type="text/plain; charset=utf-8",
        )

        streaming_response["X-Conversation-ID"] = str(conversation.id)

        return streaming_response

    return JsonResponse(
        {"error": "Method not allowed."},
        status=405,
    )


def conversation_list(request):
    conversations = Conversation.objects.order_by("-updated_at")

    data = [
        {
            "id": conversation.id,
            "title": conversation.title,
        }
        for conversation in conversations
    ]

    return JsonResponse(data, safe=False)


def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id
    )

    messages = conversation.messages.order_by("created_at")

    data = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in messages
    ]

    return JsonResponse(data, safe=False)

from django.views.decorators.http import require_POST


@require_POST
def delete_conversation(request, conversation_id):
    conversation = get_object_or_404(
        Conversation,
        id=conversation_id
    )

    conversation.delete()

    return JsonResponse({
        "success": True,
        "message": "Conversation deleted successfully."
    })
