"""Run independent specialist reviews concurrently and combine the results."""

from concurrent.futures import ThreadPoolExecutor

from common import AGENT_NAMES, create_project_client, response_text, run_agent


def main() -> None:
    request = (
        "A customer wants to order a blue trail jacket in medium using loyalty "
        "points. Identify the questions we should answer before checkout."
    )
    with create_project_client() as project_client:
        jobs = {
            "shopper": (
                "Focus only on product suitability and alternatives. Do not answer "
                "inventory or loyalty questions."
            ),
            "inventory": (
                "Focus only on availability and delivery questions. Do not answer "
                "product recommendation or loyalty questions."
            ),
            "loyalty": (
                "Focus only on points, discounts, and membership questions. Do not "
                "answer product suitability or inventory questions."
            ),
        }
        print("--- Running specialists in parallel ---")
        print("Launching: " + ", ".join(
            f"{domain.capitalize()} specialist" for domain in jobs
        ))

        def ask(item: tuple[str, str]) -> tuple[str, str]:
            domain, focus = item
            response = run_agent(
                project_client,
                AGENT_NAMES[domain],
                f"{focus}\n\nCustomer request:\n{request}",
            )
            return domain, response_text(response)

        with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
            results = dict(executor.map(ask, jobs.items()))

        for domain, answer in results.items():
            print(
                f"\n--- {domain.capitalize()} specialist is answering "
                f"(parallel result) ---\n{answer}\n"
            )


if __name__ == "__main__":
    main()
