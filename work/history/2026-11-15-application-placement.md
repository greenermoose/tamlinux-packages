# Native application placement

- **Tool:** Codex CLI 0.169.0
- **Model:** gpt-6.1-sol
- **Transcript:** Retained privately by the author.
- **Prompt:** “Get this working. I need 0.6.27 installed for testing.”

AI-assisted implementation adds the application directory to the Arch rootstock
placement profile. A product with a desktop launcher previously passed runtime
requirements but failed preparation because that directory was not permitted.
The independently versioned bootstrap becomes tam-nut 0.13.1-2; the frozen
product archive and delivery identity remain unchanged.

The bootstrap checks now prepare a sealed desktop-entry bundle in a temporary
root with the actual recovery executable and packaged profile. The regression
fails on the previous profile and passes with the correction. All six bootstrap
checks pass. The package check supplies its freshly built executable explicitly.
No test applies files to the host.
