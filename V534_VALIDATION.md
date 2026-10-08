# v5.34 validation: preferred hashtags and more title references

## Behavior

New AI-generated titles always include canonical lowercase **#fyp**. Colts titles include **#Colts #NFL #Football #fyp**, using the finished speech or the saved video title/publisher. YouTube publisher metadata is read from `import.json` when absent from `project.json`. General NFL clips use NFL/Football/fyp; other football clips use Football/fyp; unrelated topics receive fyp without forced football tags.

The app reserves the required suffix inside the 100-character title limit, then adds up to two supported optional player/topic tags if they fit. Duplicate tags are removed without dropping the required suffix. A headline that cannot fit gets a bounded repair instead of being truncated. Manual titles and reviewed drafts keep their existing protections; explicit generation requests replace their fields only after the new draft passes its checks.

The PDF profile still archives 63 posts and supplies 56 eligible title/description references. Your explicitly approved Buck/Tommy rewrite is stored in a new local corpus archive as title feedback. The writer also selects up to two related posted titles from saved Example library clips marked Good pattern and not Excluded. Two titles qualify on this Mac. Their transcripts, analytics and performance labels are not used to assert successful posting patterns. These title references are presentation data only, including when their library review status is still pending.

PDF examples, clip-title references, approved rewrites and source category metadata do not enter the independent source-check prompt. Publisher metadata supplies category tags only and is removed from the writer's style reference. The checker continues to use the final kept speech and generated headline/description. There is no model-weight training, model download or additional runtime dependency.

## Verification

- **419 regression tests passed locally**, including real video exports. After the live trial exposed a missing import-manifest fallback, all 15 posting-style tests passed with that repair and an added regression case. The posting/social tests also passed after updating the expected required suffix.
- Ruff and `git diff --check` passed.
- New coverage verifies universal fyp, category-specific defaults, source title/publisher context, the import-manifest fallback, duplicate tags, the exact 100-character boundary, no headline truncation, exclusion of bad clip references, clip-reference cache invalidation, approved rewrite relevance, factual-check separation and posting UI persistence.
- A real installed Qwen3 4B trial on the saved Buck/Tommy final transcript produced a checked How-question title with all four tags after one repair. The live app separately generated and saved a 90-character title with **#Colts #NFL #Football #fyp**, displayed v5.34, the reference count, saved-clip title references and the approved rewrite caption. The screenshot is in ignored local `work/v534-validation/hashtag-title.png`. No clip was published.
- The first trial caught the missing publisher fallback before shipment. Its temporary output and the subsequent corrected output are retained locally for debugging; the first output is not the final behavior.

## Preservation and limits

Against the 2,406-file inventory taken before this change, no files are missing and no source video, transcript, export or model-weight file changed. Changes are limited to the intended active style profile and normal app metadata: the social database, the selected project's variant/finished-clip metadata and its AI posting file. The existing manual posting entry is unchanged. Earlier PDF/corpus archives and AI copy caches remain saved.

The supplied PDF, private clip library, title feedback and raw model trials stay local and ignored by Git. Model weights and analysis-cache `modes.VERSION` remain unchanged; the user-visible version is v5.34. Hashtag presence is enforced by code and does not depend on the model following instructions. Title quality and factual source checks still require creator review, as described in v5.33; no reach or view benefit from fyp or the new reference sources is claimed.
