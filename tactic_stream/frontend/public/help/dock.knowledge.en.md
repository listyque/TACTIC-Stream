---
reference: Handler / Stream
group: Docks
icon: book-open
order: 31
---
# Knowledge Base

Knowledge Base stores project documentation as a tree of sections and Markdown articles. Open it through **Workspace panels → Browsing → Knowledge Base**. It uses the current Handler page structure, navigation, reader, editor, attachment library and history popup. Layout changes use the common dock controls.

Interface loading and download errors stay inside this dock. After updating the frontend, reload an already open browser tab if its interface download fails; local article drafts remain saved. Stable CSS files validate against the current server build instead of using an immutable cache.

## Start and permissions

An administrator initializes Knowledge Base explicitly in a project that does not have it yet. Reading never creates tables. Project and search-type access rules apply; administrators and supervisors can author and organize pages. Published pages are visible to authorized readers. Server drafts belong to their author and are hidden from other readers, including direct skey and snapshot requests.

## Browse, search and object links

The disclosure arrow expands a section; its title opens the section outline. Search matches title, summary and full text. Selecting an article opens its body and heading outline; the outline becomes inline when the reader is narrow. History, author, creation/update dates and estimated reading time accompany the document.

**Link selected objects** adds the current workspace selection to an article. Linked published articles appear as a book action on those objects. Resource previews open the object, while an article skey opens its reader. The browser address uses the real project and native record key. Copy the article key for Notes or Messages.

## Create, edit and publish

Create a section or article from the navigation toolbar. An article starts with title, summary and parent section; **Continue to content** opens the editor. Existing article metadata is available under **Show title and summary**.

**Visual** and **Markdown** edit the same canonical Markdown content. The toolbar provides headings, emphasis, lists/checklists, links, images, quotes, tables, dividers, alignment, undo and redo. Responsive overflow retains the remaining formatting actions. Python, JavaScript and XML code blocks use the shared syntax highlighting. Select an image to set its width, drag its corner or stretch it to the content width. Hover a text link to edit it.

**Save as draft** writes an unpublished server draft. **Publish** publishes it; **Save** updates an existing publication. Loading older HTML does not change the stored document until explicit saving. Save checks the revision: conflicting server edits are reported instead of overwritten.

Local editor drafts are checkpointed per login and project in browser storage. Navigating away and back restores them; unsaved content survives a page reload when storage works. Upload queues keep browser File objects only for the current page session: after a reload, select unuploaded files again. A storage failure is reported and prevents silently leaving an unsaved editor.

## Attachments

Open **Show attached files** in the formatting menu. Select files, drop them or paste clipboard files into the editor. **Paste attachment** depends on browser clipboard permission and availability, often requiring HTTPS. Uploading a new article first reserves a server draft.

Files use native FileCheckin, Snapshot, File and FileUndo. Images receive separate web/icon derivatives; original names remain in File metadata. Clicking a library card inserts its permanent original URL. A derivative is used as a display fallback, never substituted into the saved original link. The library supports copying a URL, retiring an attachment and retrying failed uploads. A previously published article stays published while adding its attachments.

## Organization, history and deletion

Move pages before/after another row or inside a section; the menu also offers explicit move actions. **Save order** applies the changes; **Discard changes** restores the server order. Cycles are rejected and a catalog revision prevents overwriting concurrent reorganization.

**Change history** loads native transaction events on demand. Selecting a revision previews its old title, summary and body; **Return to current article** exits without changing the publication. Transaction IDs keep same-second edits in the correct order.

Deleting a page uses the shared native dependency selection and DeleteCmd. A section with children must be emptied or reorganized first. An article deletion may include its own snapshots/files and uses FileUndo for rollback; unrelated linked objects are not selected for deletion automatically.

## Internal contracts

The original server procedure is `thlib/ui/knowledge_api.py`, carried into `server/knowledge_query.py`. The adapter in `server/knowledge.py` handles transport, native uploads/deletion, ACL and concurrent writes. Explicit initialization registers `{project}/th_knowledge_article`; its additional fields are `kind`, `parent_code`, `content`, `content_text`, `sort_order`, `updated_by` and `linked_skeys`. Attachments and history use standard TACTIC records, not separate web databases.

Authenticated JSON requests use `/admin/knowledge/{action}`; uploads use multipart `/admin/knowledge/upload`. Native actions include list/load, save/save_draft/reserve, organize, history/history_revision, attachments/delete_attachment and link_index. The adapter also exposes upload and dependency deletion. The `/admin/` prefix here is a backend endpoint, not a browser workspace address.

This block is verified with private native SQLite fixtures, current source QML captures and Chromium scenarios. Connected production PostgreSQL/MySQL, physical phones and arbitrary desktop clipboard formats are outside that verification. TH/DCC connections, Repository Sync and S3 remain excluded.
