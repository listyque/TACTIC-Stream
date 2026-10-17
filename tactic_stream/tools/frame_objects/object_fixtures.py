"""Matching object records and states for the original, Qt and Vue captures."""

from PySide6.QtCore import QObject, Property, Slot


class Locale(QObject):
    def __init__(self, language):
        super().__init__()
        self.language = language

    @Property(str, constant=True)
    def current_language(self):
        return self.language


class FixtureController(QObject):
    def __init__(self, model):
        super().__init__()
        self.data = model

    @Property(str, constant=True)
    def snapshot_browser_content_mode(self):
        return self.data.get("contentMode", "both")

    @Property(str, constant=True)
    def snapshot_browser_image_mode(self):
        return self.data.get("imageMode", "fit")

    @Property("QVariantMap", constant=True)
    def editor(self):
        return {
            "path": self.data.get("path", ""),
            "repositories": self.data.get("selected", []),
        }

    @Property("QVariantList", constant=True)
    def repositories(self):
        return [
            {"value": "main", "label": "Main repository"},
            {"value": "backup", "label": "Backup repository"},
        ]

    @Property(bool, constant=True)
    def editorOpen(self):
        return True

    @Property(bool, constant=True)
    def canSaveEditor(self):
        return self.data.get("canSave", False)

    @Property(bool, constant=True)
    def busy(self):
        return self.data.get("busy", False)

    @Property(str, constant=True)
    def message(self):
        return self.data.get("error", "")

    @Property("QVariantMap", constant=True)
    def presentation(self):
        return self.data

    @Property("QVariantMap", constant=True)
    def summary(self):
        return self.data.get("summary", {})

    @Property("QVariantMap", constant=True)
    def metrics(self):
        return self.data.get("metrics", {})

    @Property(bool, constant=True)
    def hasObject(self):
        return bool(self.summary)

    @Property(bool, constant=True)
    def activityHasMore(self):
        return False

    @Property(bool, constant=True)
    def activityLoadingMore(self):
        return False

    @Property(bool, constant=True)
    def deleting(self):
        return self.data.get("deleting", False)

    @Property(bool, constant=True)
    def ready(self):
        return self.data.get("ready", True)

    @Property(str, constant=True)
    def error(self):
        return self.data.get("error", "")

    @Property(int, constant=True)
    def targetCount(self):
        return self.data.get("targetCount", 1)

    @Property("QVariantList", constant=True)
    def targets(self):
        return self.data.get("targets", [])

    @Property(int, constant=True)
    def remainingTargetCount(self):
        return 0

    @Property(int, constant=True)
    def dependencyCount(self):
        return sum(row["count"] for row in self.data.get("groups", []))

    @Property(int, constant=True)
    def selectedDependencyCount(self):
        return sum(
            row["count"] for row in self.data.get("groups", []) if row.get("checked")
        )

    @Slot(int)
    def set_page(self, page):
        pass

    @Property("QVariantMap", constant=True)
    def currentTask(self):
        data = self.data
        return dict(
            code="T1",
            processRow=0,
            context=data.get("title", ""),
            status=data.get("status", ""),
            statusChoices=data.get("statuses", []),
            userChoices=data.get("users", []),
            assigned=data.get("assigned", ""),
            assignedDisplay=data.get("assignedLabel", ""),
            start=data.get("start", ""),
            end=data.get("end", ""),
            progress=data.get("progress", 0),
            progressInput=data.get("progress", 0),
            dirty=data.get("dirty", False),
            validationError="",
        )

    @Property("QVariantMap", constant=True)
    def selectedObject(self):
        return dict(
            title="Hero Robot",
            typeTitle="Assets",
            typeCode="cg/assets",
            previewUrl="",
            searchKey="cg/assets?code=A",
        )

    @Property("QVariantMap", constant=True)
    def relatedTasks(self):
        return dict(state="ready", items=[], objectCount=0, searchType="cg/assets")

    @Property(bool, constant=True)
    def taskExpanded(self):
        return True

    @Property(bool, constant=True)
    def hasTarget(self):
        return True

    @Property(bool, constant=True)
    def progressSupported(self):
        return True

    @Property("QVariantList", constant=True)
    def processChoices(self):
        return [
            dict(
                value="model",
                label="Model",
                color="#78a6c4",
                type="progress" if self.data.get("part") == "related" else "manual",
                approved=0,
                total=0,
            )
        ]

    @Property("QVariantList", constant=True)
    def taskChoices(self):
        return [dict(value="T1", label="Model"), dict(value="T2", label="Model detail")]

    @Property(str, constant=True)
    def process(self):
        return "model"

    @Property(str, constant=True)
    def processLabel(self):
        return "Model"


def report_example(loaded):
    summary = dict(
        title="Hero Robot",
        code="ASSET001",
        searchKey="cg/assets?project=cg&code=ASSET001",
        searchType="cg/assets",
        typeTitle="Assets",
        project="Computer graphics",
        pipeline="cg/assets",
        description="Robot character for the workshop scene.",
        accent="#78a6c4",
        previewUrl="",
        updatedPretty="yesterday",
        updatedFull="2026-10-16 12:00",
    )
    metrics = dict(
        tasks=1 if loaded else 0,
        activeTasks=1 if loaded else 0,
        completedTasks=0,
        overdueTasks=0,
        unassignedTasks=0,
        averageProgress=25 if loaded else 0,
        notes=1 if loaded else 0,
        children=1 if loaded else 0,
        childTypes=1 if loaded else 0,
        participants=1 if loaded else 0,
        workHours=2.5 if loaded else 0,
        files=0,
        snapshots=0,
        totalSize="0 B",
        canViewCosts=False,
    )
    task = dict(
        searchKey="sthpw/task?code=T1",
        taskCode="T1",
        process="model",
        processLabel="Model",
        processColor="#78a6c4",
        status="In progress",
        statusColor="#78a6c4",
        assigned="admin",
        assignedLabel="Administrator",
        assignedAvatar="",
        assignedColor="#437b70",
        start="",
        startPretty="",
        startFull="",
        end="",
        endPretty="",
        endFull="",
        dueState="",
        progress=25,
        description="Model the robot",
        notesCount=1,
        loggedHours=2.5,
        plannedHours=8,
    )
    person = dict(
        login="admin",
        displayName="Administrator",
        initials="A",
        avatarUrl="",
        avatarColor="#437b70",
        taskCount=1,
        noteCount=1,
        snapshotCount=0,
        hours=2.5,
        cost=0,
    )
    note = dict(
        searchKey="sthpw/note?code=N1",
        body="Review the silhouette before publishing.",
        author="admin",
        authorLabel="Administrator",
        avatarUrl="",
        initials="A",
        authorColor="#437b70",
        timestamp="2026-10-16 12:00",
        timestampPretty="yesterday",
        timestampFull="2026-10-16 12:00",
        process="model",
        taskCode="T1",
        taskTitle="Model",
        isTaskNote=True,
    )
    child = dict(
        searchKey="cg/shot?code=S1",
        title="Shot 010",
        subtitle="Workshop scene",
        typeTitle="Shots",
        typeCode="cg/shot",
        relationship="code",
        status="In progress",
        accent="#78a6c4",
        previewUrl="",
    )
    return dict(
        summary=summary,
        metrics=metrics,
        tasks=[task] if loaded else [],
        participants=[person] if loaded else [],
        notes=[note] if loaded else [],
        children=[child] if loaded else [],
        task_statuses=[
            dict(value="In progress", label="In progress", count=1, accent="#78a6c4")
        ]
        if loaded
        else [],
        task_processes=[dict(value="model", label="Model", count=1, accent="#78a6c4")]
        if loaded
        else [],
        child_types=[dict(value="cg/shot", label="Shots", count=1, accent="#78a6c4")]
        if loaded
        else [],
    )


def fixtures(smoke):
    examples = []
    for state in ("empty", "read", "edit", "pinned", "saving", "error"):
        examples.append(
            (
                "description",
                state,
                {
                    "value": ""
                    if state == "empty"
                    else "Object description\nSecond line with a longer value.",
                    "title": "Hero Robot",
                    "kind": "sobject",
                    "header": True,
                    "enabled": state != "empty",
                    "editing": state in ("edit", "error"),
                    "pinned": state == "pinned",
                    "saving": state == "saving",
                    "dirty": state in ("edit", "error"),
                    "canSave": True,
                    "error": "Unable to save description" if state == "error" else "",
                },
            )
        )
    for state in ("normal", "selected", "offline"):
        examples.append(
            (
                "summary",
                state,
                dict(
                    title="Robot_arm_geometry_with_a_very_long_name_v014.ma",
                    description="Model snapshot description",
                    version="v014",
                    revision="r02",
                    repository="Main",
                    repositoryColor="#78a6c4",
                    fileSize="12.4 MB",
                    author="admin",
                    timestamp="2026-10-17 12:00",
                    isLatest=True,
                    fileExists=state != "offline",
                    selected=state == "selected",
                    infoChips=[{"label": "Context", "value": "model"}],
                ),
            )
        )
    for mode in ("both", "preview", "files"):
        examples.append(
            (
                "toolbar",
                mode,
                dict(
                    contentMode=mode,
                    imageMode="fit",
                    orientation="horizontal",
                    showAll=False,
                    showMore=True,
                ),
            )
        )
    for state in ("empty", "selected", "error"):
        examples.append(
            (
                "watch",
                state,
                dict(
                    path="cg/assets/robot",
                    selected=[] if state == "empty" else ["main"],
                    canSave=state != "empty",
                    error="Select a valid relative path" if state == "error" else "",
                ),
            )
        )
    for state in ("normal", "required", "error", "readOnly"):
        examples.append(
            (
                "field",
                state,
                dict(
                    name="name",
                    title="Object name",
                    description="The name shown in search results",
                    icon="type",
                    required=state == "required",
                    error="Enter a unique object name" if state == "error" else "",
                    readOnly=state == "readOnly",
                ),
            )
        )
    examples.append(("report", "header", report_example(True)))
    for page in ("tasks", "notes", "children"):
        for loaded in (False, True):
            examples.append(
                (
                    "report",
                    page + ("-loaded" if loaded else "-empty"),
                    dict(report_example(loaded), page=page),
                )
            )
    for state in ("empty", "groups", "error", "deleting"):
        group = dict(
            searchType="sthpw/note",
            searchTypeTitle="Notes",
            iconName="notes",
            count=2,
            checked=True,
            defaultChecked=True,
            expanded=True,
            items=[
                dict(
                    title="Review the robot",
                    details="admin · model",
                    searchKey="sthpw/note?code=N1",
                ),
                dict(
                    title="Ready for review", details="", searchKey="sthpw/note?code=N2"
                ),
            ],
        )
        examples.append(
            (
                "delete",
                state,
                dict(
                    targetCount=1,
                    targets=[dict(title="Hero Robot", searchKey="cg/assets?code=A1")],
                    groups=[group] if state != "empty" else [],
                    ready=state != "error",
                    deleting=state == "deleting",
                    error="Read failed" if state == "error" else "",
                ),
            )
        )
    from tests.test_sobject_duplicate import _analysis_payload

    duplicate = _analysis_payload()
    duplicate["fields"] = []
    for step in (1, 2, 3, 4):
        examples.append(
            (
                "duplicate",
                str(step),
                dict(
                    duplicate,
                    step=step,
                    ready=True,
                    busy=False,
                    saving=False,
                    remember=True,
                    totals=dict(related=2, snapshots=0, tasks=0, messages=0),
                ),
            )
        )
    for state in ("empty", "loaded"):
        examples.append(("links", state, {}))
    for part in ("header", "tools", "footer"):
        for batch in (False, True):
            examples.append(
                (
                    "editor",
                    part + ("-batch" if batch else "-one"),
                    dict(
                        part=part,
                        title="Create record",
                        searchType="cg/assets",
                        mode="insert",
                        fieldCount=2,
                        valid=True,
                        batchEnabled=batch,
                        batchCount=3,
                        batchPreview=False,
                    ),
                )
            )
    for state in ("context", "quick", "related", "workHours"):
        value = dict(
            part=state,
            title="Hero Robot",
            typeTitle="Assets",
            initials="HR",
            process="model",
            processLabel="Model",
            processColor="#78a6c4",
            hasTask=True,
            canEdit=True,
            canCreate=True,
            expanded=True,
            taskCount=2,
            hasActions=False,
            progress=25,
            progressEditable=True,
            assigned="admin",
            users=[
                dict(
                    value="admin",
                    label="Administrator",
                    login="admin",
                    displayName="Administrator",
                    initials="A",
                    avatarUrl="",
                    avatarColor="#437b70",
                )
            ],
            statuses=[
                dict(value="", label=""),
                dict(value="In progress", label="In progress", color="#78a6c4"),
            ],
            status="In progress",
            assignedLabel="Administrator",
            start="2026-10-17 09:00:00",
            end="2026-10-20 18:00:00",
            summary=dict(
                planned=8, approved=2, remaining=6, overPlan=0, pending=1, progress=25
            ),
            state="ready",
            count=0,
            objectCount=0,
        )
        examples.append(("inspector", state, value))
    examples.append(
        (
            "note",
            "header",
            dict(
                author="admin",
                authorLabel="Administrator",
                initials="A",
                authorColor="#437b70",
                time="yesterday",
                fullTime="2026-10-17 12:00:00",
                actionsVisible=True,
            ),
        )
    )
    for state in ("text", "files", "emoji", "status", "edit", "delete"):
        body = (
            "Ready for review.\nSecond line with https://example.com/review"
            if state != "emoji"
            else "😀🎉"
        )
        from thlib.ui.rich_text import linkify_plain_text

        examples.append(
            (
                "note",
                state,
                dict(
                    part="edit"
                    if state == "edit"
                    else "remove"
                    if state == "delete"
                    else "body",
                    entryType="status" if state == "status" else "note",
                    statusTo="Rendering with a long status label",
                    statusColor="#78a6c4",
                    body=body,
                    displayHtml=linkify_plain_text(body),
                    text="Retained review note",
                    busy=False,
                    uncertain=False,
                    error="",
                    skeyPreviews=[],
                    attachmentCount=2 if state == "files" else 0,
                    attachments=[
                        dict(
                            title=name,
                            filename=name,
                            extension="TXT",
                            token=name,
                            href="",
                            previewUrl="",
                            size="24 B",
                            sizeText="24 B",
                            local=False,
                        )
                        for name in ("Review.txt", "Readme.txt")
                    ]
                    if state == "files"
                    else [],
                ),
            )
        )
    for screen, state, model in examples:
        for style in ("md3", "material5", "fluent"):
            for dark in (True,) if smoke else (True, False):
                for language in ("en",) if smoke else ("en", "ru"):
                    for width in (320, 880):
                        yield dict(
                            screen=screen,
                            state=state,
                            model=model,
                            style=style,
                            dark=dark,
                            language=language,
                            width=width,
                            height=59
                            if screen == "summary"
                            else 46
                            if screen == "toolbar"
                            else 320
                            if screen == "description"
                            else 640
                            if screen == "delete"
                            else 620
                            if screen == "duplicate"
                            else 420,
                        )
