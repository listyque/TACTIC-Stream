"""Attach the selected snapshot version to a VFX review, once."""

from pyasm.command import Command


class ReviewSubmissionCmd(Command):
    def execute(self):
        from pyasm.biz import Project
        from pyasm.common import Environment
        from pyasm.search import Search, SearchType

        if not Environment.get_security().is_admin():
            raise PermissionError('Administration requires administrator access')

        snapshot = Search.get_by_search_key(self.kwargs.get('snapshot_key') or '')
        if snapshot is None or snapshot.get_base_search_type() != 'sthpw/snapshot':
            raise ValueError('Choose an existing snapshot version')
        project = Project.get_project_code()
        if (
            snapshot.get_value('project_code') != project
            or int(snapshot.get_value('version')) < 1
        ):
            raise ValueError('Choose a numbered snapshot in the current project')
        if (
            snapshot.get_value('s_status', no_exception=True) == -1
            or snapshot.get_value('version') != self.kwargs.get('expected_version')
            or snapshot.get_value('context') != self.kwargs.get('expected_context')
        ):
            raise ValueError(
                'The snapshot changed. Reopen the review picker before submitting.'
            )
        parent = snapshot.get_parent()
        if parent is None or not parent.get_code():
            raise ValueError('The snapshot parent is no longer available')
        review_code = self.kwargs.get('review_code')
        if not isinstance(review_code, str) or not review_code:
            raise ValueError('Choose a review')
        review = Search('vfx/review')
        review.add_filter('code', review_code)
        if review.get_sobject() is None:
            raise ValueError('The review is no longer available')
        search = Search('vfx/submission')
        sql = search.get_sql()
        lock = getattr(sql.get_database_impl(), 'lock_collection_table', None)
        if lock:
            lock(sql, 'submission')
        elif sql.get_database_type() == 'PostgreSQL':
            sql.do_update('LOCK TABLE "submission" IN EXCLUSIVE MODE')
        else:
            raise ValueError('Review submission requires a transactional database lock')
        search.add_filter('review_code', review_code)
        search.add_filter('snapshot_code', snapshot.get_code())
        submission = search.get_sobject()
        created = submission is None
        if created:
            submission = SearchType.create('vfx/submission')
            for name, value in dict(
                review_code=review_code,
                parent_code=parent.get_code(),
                snapshot_code=snapshot.get_code(),
                artist=Environment.get_security().get_user_name(),
                search_type=snapshot.get_value('search_type'),
                context=snapshot.get_value('context'),
                version=snapshot.get_value('version'),
            ).items():
                submission.set_value(name, value)
            submission.commit()
        self.info = dict(
            created=created,
            search_key=submission.get_search_key(),
            snapshot_key=snapshot.get_search_key(),
            review_code=review_code,
        )
        return self.info
