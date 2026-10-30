# Enron Threads — Notes

## Python vs Perl: plain-language summary (with technical detail)

- **No extra software needed.** The Perl version required three add-on libraries to be installed separately. Python does the same work using tools that come built in. *(CPAN modules `Email::Address`, `JSON`, `Getopt::Std` replaced by stdlib `email.utils`, `json`, `getopt`.)*

- **Reads email addresses the same way.** Both versions parse the same email header format. Python just uses a different built-in tool to do it. *(`Email::Address->parse()` replaced by `email.utils.getaddresses()`.)*

- **Catches more addresses in the first pass.** The Enron emails contained some unusual address formats that the Perl version missed. Python adds two extra patterns to catch them. *(Handles `Name <email>@GATEWAY` gateway-wrapped addresses and `email@domain on DATE` forwarded headers.)*

- **Address extraction is tidier.** The Perl version had address-parsing logic scattered in several places. Python collects it into one function with four fallbacks tried in order. *(`parse_email_addresses()` consolidates `getaddresses` → angle-bracket regex → `[mailto:...]` → bare email regex.)*

- **Handles unusual characters without crashing.** The Perl version quietly mangled or lost non-English characters. Python explicitly declares how to handle them. *(stdin/stdout reconfigured to UTF-8 with `errors='replace'`.)*

- **Name-matching produces identical results to Perl.** The two languages handle one edge case in text-splitting differently. A small wrapper was added to make Python behave the same way. *(Python's `re.split` keeps trailing empty fields; Perl's `split` drops them — `_perl_split` replicates the Perl behaviour.)*

- **Email validation works the same way.** The rule for what counts as a valid email address is unchanged. Only the syntax for expressing it differs. *(`re.fullmatch()` replaces Perl's `=~` with anchored pattern.)*

- **Recovers a few more senders.** When the sender can't be found the normal way, Python tries one extra step before giving up. *(The `if not from_` block passes remaining `before` text through the name-lookup path as a final fallback.)*

- **The code can be reused, not just run.** The Perl scripts only work when executed directly. Python wraps the logic so it can also be imported and tested. *(`def main()` / `if __name__ == '__main__'` guard makes the module importable.)*

- **Processes all 150 mailboxes at once, not one at a time.** The original had no way to run multiple mailboxes in parallel. A new shell script runs them simultaneously, which is why the full corpus finishes in minutes rather than hours. *(`process-all-mailboxes.sh` uses `xargs -P` for parallel execution.)*

---

## Generating data tables from the JSON output

The thread JSON files are already the hard part — a new analytics script reading from `web/data/threads-*.json` could produce tables without touching the pipeline.

**Straightforward (~100-line script, no pipeline changes):**
- Thread count per user
- Shared threads between users — the `file` field in each thread is the original Enron email path, a stable identifier across mailboxes; any `file` appearing in more than one user's JSON is a shared thread
- Thread size distribution, top senders per user, most-threaded pairs

**Moderate (a bit more work, still self-contained):**
- Recipient counts — the `to` field per hop is raw text; re-parsing with `getaddresses()` extracts individual addresses
- Aggregation by any grouping (occupation, department, seniority) — straightforward once a lookup table is available; it's just a join

**The one external dependency:**
Occupation/role data is not in the corpus. The EDRM Enron dataset includes a `title` field for most employees in a separate CSV — the standard source for role analysis. It maps the 150 mailbox usernames to job titles (trader, VP, lawyer, etc.). Without it, groupings would need to be hand-coded.

**Output format** (CSV, Markdown tables, or notebook input) is the main design choice — it shapes structure more than logic.
