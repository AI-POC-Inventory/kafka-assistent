def format_response(result: dict) -> str:
    if not result or "results" not in result:
        return "⚠️ No response generated."

    outputs = []

    for step, value in result["results"].items():
        clean = value

        # Remove useless phrases
        clean = clean.replace("I have provided", "")
        clean = clean.replace("I am unable to", "")

        outputs.append(clean.strip())

    return "\n\n".join(outputs)