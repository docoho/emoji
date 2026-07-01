# Feature Roadmap

This roadmap is based on the current platform state:

- Public emoji gallery with search, category filters, likes, and favorites
- Creator workflow with drafts, submission, duplication, and creator analytics
- Public and personal collections
- Public user profiles
- Admin moderation for pending submissions

The goal is to build on the product that already exists instead of restarting with generic "social app" features.

## Priorities

### Phase 1: Discovery and Community

These are the highest-leverage additions because they make the gallery feel active without requiring a major rewrite.

#### 1. Trending and Time-Based Rankings

Why it matters:
- The app already has likes and a "popular" sort, but it does not yet answer "what is hot this week?"
- A trending shelf on the homepage gives visitors a reason to come back.

Backend changes:
- Add a lightweight `like_events` table or store `created_at` on likes if you want time-windowed ranking.
- Add endpoints or query params for `sort=trending_day`, `sort=trending_week`, and `sort=top_month`.
- Consider a small ranking helper in `backend/app/api/endpoints/emojis.py` to keep list logic readable.

Frontend changes:
- Add "Trending" and "Top This Week" options in [frontend/src/views/HomeView.vue](/Users/tiger/Documents/ai/emoji/frontend/src/views/HomeView.vue).
- Add a homepage shelf for trending emojis above the main grid.

Tests:
- Ranking order for day and week windows
- Tie-breaking behavior
- Empty-state behavior for new installs

#### 2. Comments on Emojis

Why it matters:
- Likes are a weak form of feedback.
- Comments create conversation, creator feedback loops, and more reasons for users to sign in.

Backend changes:
- Add a `Comment` model with `emoji_id`, `author_id`, `body`, `created_at`, and optional `parent_id` if you want replies later.
- Add endpoints for list/create/delete comments under `/api/emojis/{id}/comments`.
- Start with flat comments and add threads later if needed.

Frontend changes:
- Add a comment panel to the emoji modal or card detail view in [frontend/src/components/EmojiGrid.vue](/Users/tiger/Documents/ai/emoji/frontend/src/components/EmojiGrid.vue).
- Reuse `useAuth` and `useToast` for gated posting and error feedback.

Tests:
- Auth required for posting
- Owner and admin delete rules
- Comment pagination once volumes grow

#### 3. Reporting and Post-Publication Flagging

Why it matters:
- Moderation at submission time is helpful, but approved content may still need review later.
- Reporting gives the community a safety valve.

Backend changes:
- Add an `EmojiReport` model with `emoji_id`, `reporter_id`, `reason`, `details`, `status`, and timestamps.
- Add report submission endpoint and admin queue endpoints.
- Extend the admin dashboard with a second queue for reports.

Frontend changes:
- Add a "Report" action to emoji cards or the detail modal.
- Add report review UI in [frontend/src/views/AdminModerationView.vue](/Users/tiger/Documents/ai/emoji/frontend/src/views/AdminModerationView.vue).

Tests:
- Duplicate report throttling
- Admin resolution workflow
- Visibility rules for resolved reports

### Phase 2: Creator Retention

These features make the app better for repeat contributors and start turning creators into the growth engine.

#### 4. Follow Creators and Personalized Feed

Why it matters:
- The product already has public profiles and creator dashboards.
- Following is the missing connection between creator identity and recurring audience behavior.

Backend changes:
- Add a `UserFollow` join table with a unique `(follower_id, followee_id)` constraint.
- Add follow/unfollow endpoints and a `/api/feed` endpoint that returns approved emojis from followed creators.
- Extend user profile responses with follower counts and whether the current viewer follows that creator.

Frontend changes:
- Add follow buttons to [frontend/src/views/UserProfileView.vue](/Users/tiger/Documents/ai/emoji/frontend/src/views/UserProfileView.vue).
- Add a signed-in "Following" feed tab on the home page.

Tests:
- Follow uniqueness
- Prevent self-follow
- Feed ordering and visibility

#### 5. Public Creator Stats and Badges

Why it matters:
- The creator dashboard already tracks analytics privately.
- Turning some of that into public reputation makes profiles more compelling.

Backend changes:
- Extend profile payloads with public counters such as approved emojis, total likes received, and public collection count.
- Add computed badge rules such as "Top Creator", "Curated", or "Rising".

Frontend changes:
- Add a profile header module with summary metrics and badge chips.
- Optionally show badges on emoji cards and collection cards.

Tests:
- Badge eligibility rules
- Visibility rules for private or draft content

#### 6. Remix and Lineage

Why it matters:
- The creator API already supports duplication.
- Making duplication visible as a remix system encourages iteration and creative chains.

Backend changes:
- Add `source_emoji_id` to `EmojiSubmission`.
- Include lineage in emoji detail and creator responses.
- Add a "remixes" query on emoji detail pages.

Frontend changes:
- Add "Remix of ..." metadata on cards or the emoji detail view.
- Turn duplicate into an explicit "Remix" action in the creator dashboard.

Tests:
- Lineage persistence through moderation
- Deleted source behavior

### Phase 3: Better Discovery and Curation

These improve relevance and browsing depth once the social loop is stronger.

#### 7. Tag Pages and Search Improvements

Why it matters:
- Search currently relies on text fields and category.
- Tag pages create cleaner discovery paths and better SEO-like internal navigation.

Backend changes:
- Keep the existing keyword storage for now or normalize into a separate tag table later.
- Add tag aggregation endpoints and a `/api/tags/{tag}` listing endpoint.
- Add synonym expansion for common search aliases.

Frontend changes:
- Turn keywords into clickable tags across cards, modals, and collection views.
- Add tag landing pages via Vue Router.

Tests:
- Tag filtering accuracy
- Synonym matching behavior

#### 8. Featured Collections and Editorial Curation

Why it matters:
- Collections already exist, which makes editorial curation cheap to add.
- A small amount of hand-picked content can improve first impressions a lot.

Backend changes:
- Add a featured flag or featured rank for public collections.
- Add admin endpoints to manage featured collections.

Frontend changes:
- Add a featured collections shelf on the homepage.
- Highlight featured collections in [frontend/src/views/CollectionsIndexView.vue](/Users/tiger/Documents/ai/emoji/frontend/src/views/CollectionsIndexView.vue).

Tests:
- Featured ordering
- Public-only enforcement

### Phase 4: Long-Term Expansion

These are valuable, but they should come after the core social and discovery loops are healthy.

#### 9. Notifications

Examples:
- Emoji approved or rejected
- New comment on your emoji
- Added to a public collection
- New follower

Suggested approach:
- Start with in-app notifications stored in SQLite.
- Delay email or push notifications until the product has clear engagement patterns.

#### 10. Collaborative Collections

Suggested approach:
- Add collection memberships with viewer or editor roles.
- Keep collection ownership single-owner at first and layer collaboration on top.

#### 11. Exportable Emoji Packs

Suggested approach:
- Allow public collections to be exported as JSON or plain text packs.
- Good fit once collections become a stronger part of the product identity.

## Suggested Build Order

If you want the best return for the next few iterations, build in this order:

1. Trending and time-based rankings
2. Reporting and post-publication flagging
3. Comments on emojis
4. Follow creators and personalized feed
5. Public creator stats and badges
6. Remix and lineage
7. Tag pages and search improvements

This order keeps early work close to the current schema and routes, while setting up stronger creator and community loops.

## Implementation Notes

### Keep the current architecture style

- Add new tables through `init_db()` migration checks in [backend/app/db.py](/Users/tiger/Documents/ai/emoji/backend/app/db.py), consistent with the current project.
- Keep frontend API calls in [frontend/src/services/api.js](/Users/tiger/Documents/ai/emoji/frontend/src/services/api.js) using relative `/api/...` paths only.
- Reuse shared composables like `useAuth`, `useToast`, and `useCollections` instead of creating feature-local global state.

### Avoid overbuilding early

- Flat comments are enough for v1.
- In-app notifications are enough for v1.
- Tag normalization can wait until search quality becomes a real bottleneck.
- Do not introduce Redis or a job queue just to ship early social features.

### Features that fit the current codebase especially well

These have the best effort-to-impact ratio because the current routes, schemas, and UI patterns already support them well:

- Trending rankings
- Reports and moderation extensions
- Follow creators
- Remix lineage

## One-Sprint Option

If the goal is to ship one meaningful feature set quickly, the best sprint package is:

- Trending shelf on the homepage
- Report button on approved emojis
- Admin reports queue

That combination improves discovery, moderation, and trust without touching too many screens at once.
