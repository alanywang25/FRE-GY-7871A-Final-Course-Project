# Balanced media-corpus design

This is a **headline/news-card corpus plus a public Mastodon-post supplement**, not a measure of audience exposure. It is designed for coding coverage supply and framing in a prospective monitoring window. It should not be used to infer what Michigan respondents read or believed.

## Collection frame

- **News:** Google News RSS discovery queries, restricted to the 16 documented national/local publishers in `source_registry.csv`; the stored unit is the news headline/card, not a full article. The current collection searches a 60-day window and caps each source at 25 retained records per run to prevent high-volume publishers from dominating.
- **Local markets:** Atlanta, Detroit, Phoenix, Houston, Tampa Bay, Minneapolis-St. Paul, Philadelphia, and Los Angeles. Local publishers are selected to spread the sample across regions and labor/housing contexts. They do not represent all local media.
- **Social supplement:** up to three pages of public posts returned by the Mastodon public hashtag timelines for `economy`, `inflation`, and `jobs`. Public social posts are a nonrepresentative convenience stream. Retained data omit handles and display names; engagement counts are recorded only as engagement, never exposure.
- **Topic terms:** economy/economic, inflation, unemployment, jobs, wages, layoffs, prices/cost of living, GDP/growth, recession. The exact search query and retrieval timestamp are saved with every record.

## Exclusions and flags

The collector retains only news cards whose headlines themselves contain an in-scope topic term. It excludes non-English Mastodon posts where the platform language field is populated and excludes boosts/reblogs. It does not scrape article bodies, paywalled content, comments, advertisements, or user profiles. It retains candidate duplicates but labels a normalized-title/text duplicate group and defaults to one item per group for aggregate analyses. Suspected automated posts are retained but excluded by default. `suspected_automated` is a platform metadata flag, not a claim about a person.

## Required review before coding

1. Resolve news-card links to original publisher URLs where licensing permits.
2. Manually inspect source composition, duplicate groups, irrelevant results, sponsored content, and suspected automated posts.
3. Freeze the reviewed item IDs before drawing the 300-item stratified validation sample described in `docs/human_labeling_guide.md`.
4. Record actual collection and availability timestamps. RSS publication timestamps can be revised or incomplete.

The collector makes no political-balance claim and deliberately keeps political attribution as a later coding field. It separates content supply, engagement, and actual exposure.

`processed/media_corpus.csv` preserves every collected item and its inclusion flags. `processed/balanced_analysis_sample.csv` is the default coding sample: it uses equal national, local, and social strata, then selects in a round-robin sequence across publisher domains (news) or hashtag queries (social). The full corpus remains the audit trail.

`labeling/annotator_a.csv` and `labeling/annotator_b.csv` are independently randomized and source-blinded packets generated from that balanced sample. They have 315 items each, exceeding the 300-item validation minimum in the brief. Join labels back to the corpus only by `item_id` after independent completion.
