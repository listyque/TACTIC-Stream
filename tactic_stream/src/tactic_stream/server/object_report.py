"""Read-only SObjectInfo report, using the existing TACTIC record owners."""

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from pyasm.biz import File, Pipeline, Project, ProjectSetting, Task
from pyasm.common import Environment, SecurityException
from pyasm.search import Search
from pyasm.widget import ThumbWdg
from tactic.ui.table.task_element_wdg import TaskElementWdg

from .api import ApiXMLRPC
from .navigation_links import check_type, check_article_visibility
from .result_items import relations, relation_search
from .security_groups import user_identities
from .table_cells import safe_link

PAGES = ("tasks", "notes", "children", "snapshots", "activity")


def readable(search_type):
    try:
        check_type(search_type, Project.get_project_code())
    except SecurityException:
        return False
    return True


def readable_column(obj, name):
    return Environment.get_security().check_access(
        "sobject_column",
        dict(
            search_type=obj.get_base_search_type(),
            column=name,
            project=Project.get_project_code(),
        ),
        "view",
    )


def record(obj):
    data = ApiXMLRPC._record(obj)
    return {
        name: value
        for name, value in data.items()
        if name.startswith("__") or readable_column(obj, name)
    }


def related(owners, search_type):
    if not owners or not readable(search_type):
        return []
    by_type = defaultdict(list)
    for owner in owners:
        by_type[owner.get_base_search_type()].append(owner)
    result = {}
    for group in by_type.values():
        groups = Search.get_related_by_sobjects(group, search_type)
        result.update(
            (item.get_search_key(), item) for items in groups.values() for item in items
        )
    return list(result.values())


def pretty_size(value):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024


def read_report(owner, page="tasks", offset=0, limit=50):
    if page not in PAGES:
        raise ValueError("Invalid object report page")
    check_article_visibility(owner)
    visible_records = {}

    def fields(obj):
        key = obj.get_search_key()
        if key not in visible_records:
            visible_records[key] = record(obj)
        return visible_records[key]

    root = fields(owner)
    base = owner.get_base_search_type()
    tasks = [
        task
        for task in related([owner], "sthpw/task")
        if TaskElementWdg.can_view_process(task.get_value("process"))
    ]
    notes = related([owner, *tasks], "sthpw/note")
    snapshots = related([owner], "sthpw/snapshot")
    files = (
        File.get_by_snapshots(snapshots) if snapshots and readable("sthpw/file") else []
    )
    files_by_snapshot = defaultdict(list)
    for file in files:
        files_by_snapshot[file.get_value("snapshot_code")].append(file)
    display_files = {}
    for snapshot in snapshots:
        own_files = files_by_snapshot[snapshot.get_code()]
        display_files[snapshot.get_code()] = [
            file for file in own_files if file.get_type() not in ("icon", "web")
        ] or own_files
    primary_files = [file for group in display_files.values() for file in group]
    children, child_types = {}, []
    for branch in relations(owner):
        if not readable(branch["search_type"]):
            continue
        rows = relation_search(owner, branch).get_sobjects()
        child_types.append(
            dict(
                value=branch["search_type"],
                label=branch["title"],
                accent=branch["accent"],
                count=len(rows),
            )
        )
        for child in rows:
            children[child.get_search_key()] = (child, branch)

    task_by_code = {task.get_code(): task for task in tasks}
    work_hours = []
    if task_by_code and readable("sthpw/work_hour"):
        search = Search("sthpw/work_hour")
        search.add_filter("project_code", Project.get_project_code())
        search.add_filters("task_code", list(task_by_code))
        work_hours = search.get_sobjects()
    can_view_costs = readable(
        "sthpw/login"
    ) and Environment.get_security().check_access(
        "sobject_column",
        dict(
            search_type="sthpw/login",
            column="hourly_wage",
            project=Project.get_project_code(),
        ),
        "view",
    )
    logins = set()
    for objects, name in (
        (tasks, "assigned"),
        (notes, "login"),
        (snapshots, "login"),
        (work_hours, "login"),
    ):
        logins.update(fields(obj)[name] for obj in objects if fields(obj).get(name))
    users = (
        Search.get_by_code("sthpw/login", list(logins))
        if logins and readable("sthpw/login")
        else []
    )
    identities = {user["login"]: user for user in user_identities(users)}
    wages = (
        {
            user.get_value("login"): float(user.get_value("hourly_wage") or 0)
            for user in users
        }
        if can_view_costs
        else {}
    )
    hours, costs, task_hours = (
        defaultdict(float),
        defaultdict(float),
        defaultdict(float),
    )
    for entry in work_hours:
        value = (
            float(entry.get_total_hours())
            if all(
                readable_column(entry, name)
                for name in ("straight_time", "over_time", "category")
            )
            else 0
        )
        login = fields(entry).get("login")
        hours[login] += value
        costs[login] += value * wages.get(login, 0)
        task_hours[fields(entry).get("task_code")] += value

    pipeline = (
        Pipeline.get_by_code(root.get("pipeline_code"))
        if root.get("pipeline_code")
        else None
    )
    statuses, processes, task_rows = {}, {}, []
    today = date.today()
    for task in tasks:
        data = fields(task)
        process, status = data.get("process", ""), data.get("status", "")
        node = pipeline.get_process(process) if pipeline else None
        color = node.get_color() if node else ""
        label = node.get_label() or process if node else process
        task_pipeline = task.get_pipeline()
        status_node = (
            task_pipeline.get_process(status) if task_pipeline and status else None
        )
        status_color = status_node.get_color() if status_node else color
        completion = task.get_completion() if status else 0
        progress = data.get("progress", data.get("completion"))
        progress = max(
            0,
            min(
                100,
                int(float(progress if progress not in (None, "") else completion or 0)),
            ),
        )
        end = str(data.get("bid_end_date") or "")
        due = end[:10]
        assigned = identities.get(data.get("assigned"), {})
        unit = ProjectSetting.get_value_by_key("bid_duration_unit")
        task_rows.append(
            dict(
                searchKey=task.get_search_key(),
                taskCode=task.get_code(),
                process=process,
                processLabel=label,
                processColor=color,
                status=status,
                statusColor=status_color,
                assigned=data.get("assigned") or "",
                assignedLabel=assigned.get("displayName") or data.get("assigned") or "",
                assignedAvatar=assigned.get("avatarUrl", ""),
                assignedColor=assigned.get("avatarColor", ""),
                start=str(data.get("bid_start_date") or ""),
                end=end,
                endPretty=end,
                endFull=end,
                dueState="overdue"
                if due and due < today.isoformat() and progress < 100
                else "",
                progress=progress,
                description=data.get("description") or "",
                notesCount=sum(
                    fields(note).get("search_code") == task.get_code() for note in notes
                ),
                loggedHours=round(task_hours[task.get_code()], 2),
                plannedHours=float(data.get("bid_duration") or 0)
                / (60 if unit == "minute" else 1),
            )
        )
        for catalog, value, title, accent in (
            (statuses, status, status, status_color),
            (processes, process, label, color),
        ):
            row = catalog.setdefault(
                value, dict(value=value, label=title, accent=accent, count=0)
            )
            row["count"] += 1

    participants = []
    for login in sorted(logins):
        identity = identities.get(login, {})
        participants.append(
            dict(
                login=login,
                displayName=identity.get("displayName") or login,
                initials=identity.get("initials") or login[:2].upper(),
                avatarUrl=identity.get("avatarUrl", ""),
                avatarColor=identity.get("avatarColor", ""),
                taskCount=sum(fields(task).get("assigned") == login for task in tasks),
                noteCount=sum(fields(note).get("login") == login for note in notes),
                snapshotCount=sum(
                    fields(snapshot).get("login") == login for snapshot in snapshots
                ),
                hours=round(hours[login], 2),
                **(dict(cost=round(costs[login], 2)) if can_view_costs else {}),
            )
        )
    thumb = ThumbWdg(latest_icon="true", protocol="http")
    preview_objects = [
        owner,
        *(child for child, _branch in children.values()),
        *(snapshots if page == "snapshots" else []),
    ]
    thumb.set_sobjects(preview_objects)
    thumb.preprocess()
    previews = {}
    for index, obj in enumerate(preview_objects):
        thumb.set_current_index(index)
        previews[obj.get_search_key()] = thumb.get_cell_value().get("image", "")
    updated = str(root.get("last_updated") or root.get("timestamp") or "")
    summary = dict(
        title=root.get("name")
        or root.get("title")
        or root.get("code")
        or str(root.get("id", "")),
        searchKey=owner.get_search_key(),
        code=str(root.get("code") or ""),
        searchType=base,
        typeTitle=owner.get_search_type_obj().get_title(),
        project=Project.get().get_value("title") or Project.get_project_code(),
        pipeline=root.get("pipeline_code") or "",
        description=root.get("description") or "",
        accent=owner.get_search_type_obj().get_value("color", no_exception=True) or "",
        previewUrl=previews[owner.get_search_key()],
        updatedPretty=updated,
        updatedFull=updated,
    )
    total_size = sum(int(fields(file).get("st_size") or 0) for file in primary_files)
    metrics = dict(
        tasks=len(tasks),
        activeTasks=sum(row["progress"] < 100 for row in task_rows),
        completedTasks=sum(row["progress"] >= 100 for row in task_rows),
        overdueTasks=sum(row["dueState"] == "overdue" for row in task_rows),
        unassignedTasks=sum(not row["assigned"] for row in task_rows),
        dueThisWeek=sum(
            today.isoformat()
            <= row["end"][:10]
            < (today + timedelta(days=7)).isoformat()
            for row in task_rows
        ),
        averageProgress=round(
            sum(row["progress"] for row in task_rows) / len(task_rows)
        )
        if task_rows
        else 0,
        notes=len(notes),
        objectNotes=sum(
            fields(note).get("search_code") == owner.get_code() for note in notes
        ),
        taskNotes=sum(
            fields(note).get("search_code") in task_by_code for note in notes
        ),
        children=len(children),
        childTypes=len(child_types),
        participants=len(participants),
        workHours=round(sum(hours.values()), 2),
        canViewCosts=can_view_costs,
        snapshots=len(snapshots),
        files=len(primary_files),
        totalSize=pretty_size(total_size),
        **(dict(totalCost=round(sum(costs.values()), 2)) if can_view_costs else {}),
    )
    result = dict(
        summary=summary,
        metrics=metrics,
        task_statuses=list(statuses.values()),
        task_processes=list(processes.values()),
        participants=participants,
        child_types=child_types,
        properties=[
            dict(label=name, value=str(value))
            for name, value in root.items()
            if not name.startswith("__") and value not in (None, "")
        ][:24],
        tasks=[],
        notes=[],
        children=[],
        snapshots=[],
        files=[],
        snapshot_processes=[],
        activity=[],
        hasMore=False,
    )
    if page == "tasks":
        result["tasks"] = task_rows
    elif page == "notes":
        for note in sorted(
            notes,
            key=lambda note: str(fields(note).get("timestamp") or ""),
            reverse=True,
        ):
            data = fields(note)
            identity = identities.get(data.get("login"), {})
            task = task_by_code.get(data.get("search_code"))
            stamp = str(data.get("timestamp") or "")
            result["notes"].append(
                dict(
                    searchKey=note.get_search_key(),
                    body=data.get("note") or "",
                    author=data.get("login") or "",
                    authorLabel=identity.get("displayName") or data.get("login") or "",
                    avatarUrl=identity.get("avatarUrl", ""),
                    initials=identity.get("initials", ""),
                    authorColor=identity.get("avatarColor", ""),
                    timestamp=stamp,
                    timestampPretty=stamp,
                    timestampFull=stamp,
                    process=data.get("process") or data.get("context") or "",
                    taskCode=task.get_code() if task else "",
                    taskTitle=fields(task).get("process", "") if task else "",
                    isTaskNote=bool(task),
                )
            )
    elif page == "children":
        for child, branch in children.values():
            data = fields(child)
            result["children"].append(
                dict(
                    searchKey=child.get_search_key(),
                    title=data.get("name")
                    or data.get("title")
                    or data.get("code")
                    or str(child.get_id()),
                    subtitle=data.get("description") or "",
                    typeTitle=branch["title"],
                    typeCode=branch["search_type"],
                    relationship=branch["relationship"],
                    status=data.get("status") or data.get("s_status") or "",
                    accent=branch["accent"],
                    previewUrl=previews[child.get_search_key()],
                )
            )
    elif page == "snapshots":
        groups = defaultdict(list)
        for snapshot in snapshots:
            groups[(fields(snapshot).get("context") or "").split("/")[0]].append(
                snapshot
            )
        for process, process_snapshots in groups.items():
            process_rows, process_files = [], []
            node = pipeline.get_process(process) if pipeline else None
            for snapshot in sorted(
                process_snapshots,
                key=lambda obj: (
                    str(fields(obj).get("context") or ""),
                    -int(fields(obj).get("version") or 0),
                ),
            ):
                data = fields(snapshot)
                own_files = display_files[snapshot.get_code()]
                total = sum(int(fields(file).get("st_size") or 0) for file in own_files)
                title = data.get("description") or data.get("context") or process
                stamp = str(data.get("timestamp") or "")
                versionless = int(data.get("version") or 0) < 0
                process_rows.append(
                    dict(
                        searchKey=snapshot.get_search_key(),
                        modelIndex=len(result["snapshots"]),
                        process=process,
                        title=title,
                        context=data.get("context") or "",
                        version="Current"
                        if versionless
                        else f"v{int(data.get('version') or 0):03d}",
                        author=identities.get(data.get("login"), {}).get("displayName")
                        or data.get("login")
                        or "",
                        timestamp=stamp,
                        timestampPretty=stamp,
                        timestampFull=stamp,
                        previewUrl=previews.get(snapshot.get_search_key(), ""),
                        fileCount=len(own_files),
                        sizeText=pretty_size(total),
                        repository=data.get("repo") or "base",
                        isLatest=bool(data.get("is_latest")),
                        isVersionless=versionless,
                    )
                )
                result["snapshots"].append(process_rows[-1])
                descriptors = []
                ThumbWdg.get_file_info(
                    snapshot.get_xml_value("snapshot"),
                    {
                        file.get_code(): file
                        for file in files_by_snapshot[snapshot.get_code()]
                    },
                    snapshot,
                    snapshot,
                    files=descriptors,
                )
                urls = {file["code"]: file["href"] for file in descriptors}
                for file in own_files:
                    path = Path(file.get_lib_path())
                    file_type = file.get_type()
                    href = safe_link(urls.get(file.get_code(), ""))
                    process_files.append(
                        dict(
                            token=file.get_code(),
                            searchKey=file.get_search_key(),
                            title=file.get_full_file_name(),
                            extension=path.suffix.lstrip("."),
                            type=file_type,
                            sizeText=pretty_size(int(fields(file).get("st_size") or 0)),
                            path=path.as_posix(),
                            size=int(fields(file).get("st_size") or 0),
                            repository=data.get("repo") or "base",
                            exists=path.exists(),
                            previewUrl=href
                            if file_type in ("image", "icon", "web")
                            else "",
                            href=href,
                        )
                    )
            result["files"].extend(process_files)
            result["snapshot_processes"].append(
                dict(
                    value=process,
                    label=node.get_label() or process if node else process,
                    accent=node.get_color() if node else "",
                    snapshotCount=len(process_rows),
                    fileCount=len(process_files),
                    sizeText=pretty_size(
                        sum(
                            int(fields(file).get("st_size") or 0)
                            for snapshot in process_snapshots
                            for file in display_files[snapshot.get_code()]
                        )
                    ),
                    snapshots=process_rows,
                    files=sorted(
                        process_files, key=lambda row: row["title"].casefold()
                    ),
                )
            )
        result["snapshot_processes"].sort(key=lambda row: row["label"].casefold())
    elif page == "activity":
        check_type("sthpw/transaction_log", Project.get_project_code())
        from .activity_query import query_user_recent_activity
        from .activity_feed import instance_relations, decorate_activity

        scope = dict(
            searchType=base,
            searchCode=owner.get_code(),
            searchId=str(owner.get_id()),
            childTypes=[row["value"] for row in child_types],
            noteCodes=[note.get_code() for note in notes],
            snapshotCodes=[snapshot.get_code() for snapshot in snapshots],
            workHourCodes=[entry.get_code() for entry in work_hours],
        )
        activity = query_user_recent_activity(
            project_code=Project.get_project_code(),
            object_scope=scope,
            instance_relations=instance_relations(),
            offset=offset,
            limit=limit + 1,
        )
        rows = activity.get("records", []) if isinstance(activity, dict) else activity
        actor_logins = list({row.get("actor") for row in rows if row.get("actor")})
        actors = (
            Search.get_by_code("sthpw/login", actor_logins)
            if actor_logins and readable("sthpw/login")
            else []
        )
        decorate_activity(
            rows, {user["login"]: user for user in user_identities(actors)}
        )
        result.update(activity=rows[:limit], hasMore=len(rows) > limit)
    return result
