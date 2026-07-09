from app.core.text_quality import find_missing_portuguese_accents, is_linkedin_post_text_quality_ok


def test_find_missing_portuguese_accents_ignores_hashtags():
    text = "Dados publicos precisam de revisao humana. #DadosPublicos"

    assert find_missing_portuguese_accents(text) == ["publicos", "revisao"]


def test_linkedin_post_text_quality_accepts_accented_body_with_plain_hashtags():
    text = "Dados públicos precisam de revisão humana. #DadosPublicos"

    assert is_linkedin_post_text_quality_ok(text)
