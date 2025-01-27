from resources.model_resource.services.api_key_service import _auth_helm_api_key, _auth_openai_api_key, _auth_anthropic_api_key

def test_auth_helm_api_key():
    assert _auth_helm_api_key("obviously_invalid_api_key", "")[0] is False

    valid_api_key = input("Enter a valid HELM API key: ")
    assert _auth_helm_api_key(valid_api_key)[0] is True


def test_auth_openai_api_key():
    assert _auth_openai_api_key("obviously_invalid_api_key")[0] is False

    valid_api_key = input("Enter a valid OpenAI API key: ")
    assert _auth_openai_api_key(valid_api_key)[0] is True


def test_auth_anthropic_api_key():
    assert _auth_anthropic_api_key("obviously_invalid_api_key")[0] is False

    valid_api_key = input("Enter a valid Anthropic API key: ")
    assert _auth_anthropic_api_key(valid_api_key)[0] is True


if __name__ == "__main__":
    test_auth_helm_api_key()
    print(" - auth_helm_api_key passed")

    test_auth_openai_api_key()
    print(" - auth_openai_api_key passed")

    test_auth_anthropic_api_key()
    print(" - auth_anthropic_api_key passed")
