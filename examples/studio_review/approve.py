from pyasm.common import Environment
from pyasm.search import Search

code = kwargs.get('review_code') or kwargs.get('input', {}).get('review_code')
if not code:
    raise ValueError('Pass review_code, for example STUDIO_REVIEW_001')
review = Search.get_by_code('studio/review', code)
if review is None:
    raise ValueError('Review does not exist in this project')
review.set_value('status', 'Approved')
review.set_value('progress', 100)
review.set_value('approved_by', Environment.get_user_name())
review.commit()
return dict(code=code, status=review.get_value('status'), progress=review.get_value('progress'))
