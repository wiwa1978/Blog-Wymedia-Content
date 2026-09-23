"""Run a sequential analyst-to-reviewer workflow."""

from common import AGENT_NAMES, create_project_client, response_text, run_agent


def main() -> None:
    request = (
        "We want to recommend a waterproof trail jacket to a runner who hikes "
        "on weekends. Explain the recommendation and the assumptions."
    )
    with create_project_client() as project_client:
        print("--- Shopper specialist is answering ---")
        draft = run_agent(project_client, AGENT_NAMES["shopper"], request)
        print("Draft:\n" + response_text(draft))
        review_prompt = (
            "Review this draft for unsupported claims and missing assumptions. "
            "Return a corrected, concise version.\n\nDRAFT:\n"
            + response_text(draft)
        )
        print("\n--- Reviewer specialist is answering ---")
        review = run_agent(project_client, AGENT_NAMES["reviewer"], review_prompt)
        print("Review:\n" + response_text(review))


if __name__ == "__main__":
    main()
