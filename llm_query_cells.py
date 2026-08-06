import boto3
import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any
from IPython.display import display, Markdown

# ─────────────────────────────────────────────────────────────────────────────
# Verify AWS credentials are available in this environment
# ─────────────────────────────────────────────────────────────────────────────
_required_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"]
_missing = [v for v in _required_vars if not os.environ.get(v)]
if _missing:
    raise EnvironmentError(
        f"Missing AWS credentials in environment: {', '.join(_missing)}\n"
        f"Make sure you export these in the same shell/environment where you run this script:\n"
        f"  export AWS_ACCESS_KEY_ID=\"...\"\n"
        f"  export AWS_SECRET_ACCESS_KEY=\"...\"\n"
        f"  export AWS_SESSION_TOKEN=\"...\"\n"
        f"  export AWS_REGION=\"us-west-2\""
    )


# ─────────────────────────────────────────────────────────────────────────────
# MODEL CATALOGUE
# Change ACTIVE_MODEL to any key below to swap models instantly.
# ─────────────────────────────────────────────────────────────────────────────

class Model(str, Enum):
    CLAUDE_SONNET_4_6 = "us.anthropic.claude-sonnet-4-6"
    # CLAUDE_HAIKU_4_5  = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


# ─────────────────────────────────────────────────────────────────────────────
# *** SWAP HERE — change to any Model.* value to switch the active model ***
# ─────────────────────────────────────────────────────────────────────────────
ACTIVE_MODEL: Model = Model.CLAUDE_SONNET_4_6


# ─────────────────────────────────────────────────────────────────────────────
# Request / Response dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class LLMRequest:
    """Encapsulates a single text inference request."""
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9


@dataclass
class LLMResponse:
    """Normalised response from any text model."""
    model_id: str
    text: Optional[str] = None
    raw: Optional[dict] = None
    input_tokens: int = 0
    output_tokens: int = 0

    def display(self):
        """Print the response text and token usage."""
        if self.text:
            print(self.text)
        print(
            f"\n---\nModel: {self.model_id} | "
            f"Input tokens: {self.input_tokens} | "
            f"Output tokens: {self.output_tokens}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Core client
# ─────────────────────────────────────────────────────────────────────────────

class BedrockLLMClient:
    """
    Unified text-only client for Amazon Bedrock foundation models.

    Usage
    -----
    client = BedrockLLMClient()                              # uses ACTIVE_MODEL
    client = BedrockLLMClient(model=Model.CLAUDE_HAIKU_4_5)  # explicit model
    response = client.invoke(LLMRequest(prompt="Hello!"))
    response.display()
    """

    def __init__(self, model: Model = ACTIVE_MODEL):
        self.model = model
        self.region = os.environ.get("AWS_REGION", "us-west-2")
        self._bedrock = boto3.client("bedrock-runtime", region_name=self.region)

    def _build_inference_config(self, request: LLMRequest) -> dict:
        """Build inferenceConfig — Claude models only accept temperature, not top_p."""
        return {
            "maxTokens": request.max_tokens,
            "temperature": request.temperature,
        }

    def invoke(self, request: LLMRequest) -> LLMResponse:
        """Send a text prompt via the Converse API."""
        messages = [{"role": "user", "content": [{"text": request.prompt}]}]
        inference_cfg = self._build_inference_config(request)

        kwargs: dict[str, Any] = {
            "modelId": self.model.value,
            "messages": messages,
            "inferenceConfig": inference_cfg,
        }
        if request.system_prompt:
            kwargs["system"] = [{"text": request.system_prompt}]

        try:
            raw = self._bedrock.converse(**kwargs)
        except Exception as exc:
            raise RuntimeError(
                f"Bedrock converse call failed for model '{self.model.value}': {exc}"
            ) from exc

        output_msg = raw.get("output", {}).get("message", {})
        text_parts = [
            blk["text"]
            for blk in output_msg.get("content", [])
            if "text" in blk
        ]
        usage = raw.get("usage", {})
        return LLMResponse(
            model_id=self.model.value,
            text="\n".join(text_parts),
            raw=raw,
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Convenience helper — single function call interface
# ─────────────────────────────────────────────────────────────────────────────

def ask(
    prompt: str,
    *,
    model: Model = ACTIVE_MODEL,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    auto_display: bool = True,
) -> LLMResponse:
    """
    One-liner text inference call.

    Parameters
    ----------
    prompt        : Your text prompt / question.
    model         : Override the active model (Model.* enum value).
    system_prompt : Optional system instruction.
    max_tokens    : Maximum output tokens.
    temperature   : Sampling temperature (0–1).
    auto_display  : Automatically render the response in the notebook.

    Returns
    -------
    LLMResponse object (always returned regardless of auto_display).

    Examples
    --------
    # Uses ACTIVE_MODEL
    response = ask("Explain quantum entanglement in simple terms.")

    # Override model inline
    response = ask("Write a haiku.", model=Model.CLAUDE_HAIKU_4_5)
    """
    client = BedrockLLMClient(model=model)
    req = LLMRequest(
        prompt=prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    response = client.invoke(req)
    if auto_display:
        response.display()
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Quick-start demo  (comment out or delete after testing)
# ─────────────────────────────────────────────────────────────────────────────

print(f"✅ BedrockLLMClient ready.  Active model → {ACTIVE_MODEL.value}\n")
print("Available models:")
for m in Model:
    marker = " ◀ ACTIVE" if m == ACTIVE_MODEL else ""
    print(f"  Model.{m.name:<30} {m.value}{marker}")

print("\n─── Running a quick test with the active model ───")
_ = ask("In one sentence, what is Amazon Bedrock?")





from pypdf import PdfReader

def get_pdf_text(pdf_path):
    # Load the PDF file
    reader = PdfReader(pdf_path)

    # Extract text from all pages
    extracted_text = []
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            extracted_text.append(f"\n{text}")

    # Join all pages into a single string
    return("\n\n".join(extracted_text))

legislation_full_text = get_pdf_text("scripts/Australian-Federal-Police-Act-Australia-1979.pdf")
johnny_english_text = get_pdf_text("scripts/johnny_english.pdf")
austin_powers_text = get_pdf_text("scripts/austin_powers_script.pdf")
barbie_text = get_pdf_text("scripts/barbie_script.pdf")
team_america = get_pdf_text("scripts/team_america.pdf")
# Preview the first 2000 characters
print(f"legislation_full_text: {len(legislation_full_text)}")
print(f"johnny_english_text: {len(johnny_english_text)}")
print(f"austin_powers_text: {len(austin_powers_text)}")
print(f"barbie_text: {len(barbie_text)}")
print(f"team_america: {len(team_america)}")









ask(f"""I will provide 2 pieces of text - the legislation for the AFP and the script of a movie.
----------
Legislation:
{legislation_full_text}
----------
Movie script:
{johnny_english_text}
----------
Can you provide suggestions for how the characters could have acted differently to align better with the AFP legislation?
Provide specific examples from the movie script and the legislation
Give each character a score out of 10 as to how well they complied with the AFP legislation
""",
model=Model.CLAUDE_SONNET_4_6)

