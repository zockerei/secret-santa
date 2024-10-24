from flask import render_template
from . import christmas
from app.decorators import login_required

@christmas.route('/christmas')
@login_required(role='participant')
def christmas():
    """Display the christmas page."""

    return render_template('christmas.html')
