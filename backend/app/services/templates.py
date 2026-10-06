import re

PLACEHOLDER = re.compile(r"\{\{(\d+)\}\}")


def placeholder_count(body: str) -> int:
    return max((int(n) for n in PLACEHOLDER.findall(body)), default=0)


def render(body: str, variables: list[str]) -> str:
    def fill(match: re.Match) -> str:
        index = int(match.group(1)) - 1
        return variables[index] if 0 <= index < len(variables) else match.group(0)

    return PLACEHOLDER.sub(fill, body)
