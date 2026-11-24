# Contributing

Thanks for helping engineers save money! This list is for deals that are useful to **DevOps, SRE, Platform, Cloud and MLOps engineers**.

## What we accept

- Learning platforms, labs, courses, interview prep and system design for DevOps, cloud, Kubernetes, SRE or MLOps
- Tech books and reading platforms
- Certification exams and bundles (Linux Foundation, CNCF, AWS, Azure, GCP, HashiCorp and so on)
- Web, VPS and managed cloud hosting
- Creator tools that help engineers share what they know: blogs, newsletters, courses, demos
- Real discounts with a clear offer. No "contact sales" or fake "was $999" prices.

## The easy way: open an issue

[Open a deal request](../../issues/new?template=submit-deal.yml) and fill in the form. A maintainer will check it and add it.

## The developer way: open a pull request

1. Fork the repo and create a branch from `dev`.
2. Add your deal to [`deals.yml`](deals.yml) under the right category (or the right group inside Certifications). Deals show in the same order as in the file. Copy this block:

   ```yaml
   - name: KodeKloud                 # product name
     domain: kodekloud.com            # used for the logo
     url: https://kodekloud.com/      # official deal page, https only
     description: Hands-on DevOps courses with in-browser labs   # one short line
     offer: 50% off annual plans      # what the reader gets
     code: BF2026                     # optional, leave out if no code is needed
                                      # use `code: soon` to show a ⏳ "Code coming soon" button
     valid: Ends Dec 2                # optional, deadline or date range
     status: live                     # live | soon | expired
   ```

3. Rebuild the README:

   ```bash
   pip install pyyaml
   python scripts/build_readme.py
   ```

4. Commit both `deals.yml` and `README.md`, then open a pull request to the `dev` branch.

> [!IMPORTANT]
> Don't edit the tables in `README.md` by hand. They are generated from `deals.yml`, and the CI check fails if they don't match.

## Rules

- One product per entry. Check the list first so you don't add a duplicate.
- Keep `description` to one short line, and don't use the `|` character.
- Link to the vendor's official page.
- Mark a deal `expired` when it ends instead of deleting it during the sale.

## What the CI checks

The **Validate deals** workflow runs `python scripts/build_readme.py --check` on every pull request. It checks that:

- every deal has the required fields
- every `url` starts with `https://`
- `status` is `live`, `soon` or `expired`
- `README.md` matches `deals.yml`
