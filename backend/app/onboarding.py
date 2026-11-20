"""The onboarding checklist. Each task links to a question the assistant can answer,
so new employees learn by asking. Edit this list to change the journey."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    description: str
    ask: str  # opens the chat with this question
    roles: tuple[str, ...] = ("employee", "manager", "admin")


TASKS = [
    Task("laptop", "Set up your laptop", "Log in, change your password and install the company apps.",
         "How do I set up my laptop on my first day?"),
    Task("security", "Turn on two-factor authentication", "Store passwords in 1Password and protect your accounts.",
         "Where should I store passwords and which accounts need 2FA?"),
    Task("vpn", "Get VPN access", "You need it for Jira, the wiki and dashboards when working remotely.",
         "Which VPN client do I need to install?"),
    Task("conduct", "Read the code of conduct", "Know what we expect and how to raise a concern.",
         "How can I report a problem anonymously?"),
    Task("time-off", "Learn how time off works", "Paid time off, carry-over and sick leave.",
         "How many vacation days do new employees get?"),
    Task("expenses", "Learn how to claim expenses", "Receipts, limits and travel booking.",
         "How do I submit expenses and what is the meal allowance?"),
    Task("reviews", "Know when performance reviews happen", "Self-review, probation and salary changes.",
         "When do performance reviews happen?"),
    Task("salary-bands", "Review the salary bands", "For managers: bands and approval rules for offers.",
         "What are the salary bands for engineers?", roles=("manager", "admin")),
]

QUIZ_TASK = "quiz"
QUIZ_PASS_PERCENT = 80


def tasks_for(role: str) -> list[Task]:
    return [task for task in TASKS if role in task.roles]
