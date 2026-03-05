from zotero_arxiv_daily.protocol import Paper


def _build_paper() -> Paper:
    return Paper(
        source="arxiv",
        title="test",
        authors=["a"],
        abstract="",
        url="https://example.com",
    )


def test_parse_affiliations_json_list():
    paper = _build_paper()
    raw = '["TsingHua University","Peking University"]'
    assert paper._parse_affiliations_response(raw) == [
        "TsingHua University",
        "Peking University",
    ]


def test_parse_affiliations_python_list_with_prefix_text():
    paper = _build_paper()
    raw = "Affiliations found: ['MIT', 'Stanford University', 'MIT']"
    assert paper._parse_affiliations_response(raw) == [
        "MIT",
        "Stanford University",
    ]


def test_parse_affiliations_invalid_text_returns_empty_list():
    paper = _build_paper()
    assert paper._parse_affiliations_response("No affiliations detected.") == []


class _MockMessage:
    def __init__(self, content: str):
        self.content = content


class _MockChoice:
    def __init__(self, content: str):
        self.message = _MockMessage(content)


class _MockResponse:
    def __init__(self, content: str):
        self.choices = [_MockChoice(content)]


class _MockCompletions:
    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _MockResponse('["MIT"]')


class _MockChat:
    def __init__(self):
        self.completions = _MockCompletions()


class _MockOpenAI:
    def __init__(self):
        self.chat = _MockChat()


def test_generate_affiliations_uses_dedicated_model_override():
    paper = _build_paper()
    paper.full_text = "author affiliations"
    client = _MockOpenAI()
    llm_params = {
        "generation_kwargs": {"model": "model-for-tldr", "max_tokens": 512},
        "affiliations_generation_kwargs": {"model": "model-for-affiliations"},
    }
    paper.generate_affiliations(client, llm_params)
    assert paper.affiliations == ["MIT"]
    assert client.chat.completions.last_kwargs["model"] == "model-for-affiliations"
    assert client.chat.completions.last_kwargs["max_tokens"] == 512
