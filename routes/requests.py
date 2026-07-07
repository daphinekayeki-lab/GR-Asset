"""
Asset Request & Return Request routes — GR AMS
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import AssetRequest, ReturnRequest, Asset, AssetCategory, User
from extensions import db
from datetime import datetime, date
from functools import wraps

requests_bp = Blueprint('requests', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('admin', 'finance'):
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
#  ASSET REQUESTS (borrow a new asset)
# ─────────────────────────────────────────────

@requests_bp.route('/asset-requests')
@login_required
def asset_requests():
    if current_user.role in ('admin', 'finance'):
        # Admin sees all pending first, then others
        items = AssetRequest.query.order_by(
            AssetRequest.status.asc(),
            AssetRequest.requested_at.desc()
        ).all()
    else:
        items = AssetRequest.query.filter_by(requested_by_id=current_user.id)\
                                  .order_by(AssetRequest.requested_at.desc()).all()
    categories = AssetCategory.query.order_by(AssetCategory.name).all()
    return render_template('requests/asset_requests.html',
                           requests=items, categories=categories)


@requests_bp.route('/asset-requests/new', methods=['GET', 'POST'])
@login_required
def new_asset_request():
    if request.method == 'POST':
        from_str = request.form.get('date_needed_from', '')
        to_str   = request.form.get('date_needed_to', '')
        try:
            date_from = date.fromisoformat(from_str) if from_str else None
            date_to   = date.fromisoformat(to_str)   if to_str   else None
            duration  = (date_to - date_from).days + 1 if date_from and date_to else None
        except ValueError:
            date_from = date_to = duration = None

        req = AssetRequest(
            requested_by_id  = current_user.id,
            item_requested   = request.form['item_requested'].strip(),
            purpose          = request.form['purpose'].strip(),
            date_needed_from = date_from,
            date_needed_to   = date_to,
            duration_days    = duration,
            category_id      = request.form.get('category_id') or None,
            status           = 'pending',
        )
        db.session.add(req)
        db.session.commit()
        flash('✓ Asset request submitted. You will be notified once reviewed.', 'success')
        return redirect(url_for('requests.asset_requests'))

    categories = AssetCategory.query.order_by(AssetCategory.name).all()
    return render_template('requests/new_asset_request.html', categories=categories)


@requests_bp.route('/asset-requests/<int:req_id>/review', methods=['GET', 'POST'])
@login_required
@admin_required
def review_asset_request(req_id):
    req = AssetRequest.query.get_or_404(req_id)

    # Available unassigned assets
    available = Asset.query.filter_by(assigned_to_id=None, status='active')\
                           .order_by(Asset.name).all()
    if req.category_id:
        suggested = [a for a in available if a.category_id == req.category_id]
    else:
        suggested = available

    if request.method == 'POST':
        action = request.form.get('action')  # approve | reject
        req.reviewed_by_id = current_user.id
        req.reviewed_at    = datetime.utcnow()
        req.admin_note     = request.form.get('admin_note', '').strip()

        if action == 'approve':
            asset_id = request.form.get('assigned_asset_id')
            if not asset_id:
                flash('Please select an asset to assign.', 'error')
                return render_template('requests/review_asset_request.html',
                                       req=req, suggested=suggested, available=available)
            asset = Asset.query.get_or_404(int(asset_id))
            # Assign the asset
            asset.assigned_to_id = req.requested_by_id
            asset.assigned_on    = date.today()
            req.assigned_asset_id = asset.id
            req.status = 'approved'
            db.session.commit()
            flash(f'✓ Request approved. {asset.tag} assigned to {req.requested_by.name}.', 'success')

        elif action == 'reject':
            req.status = 'rejected'
            db.session.commit()
            flash(f'Request from {req.requested_by.name} rejected.', 'success')

        return redirect(url_for('requests.asset_requests'))

    return render_template('requests/review_asset_request.html',
                           req=req, suggested=suggested, available=available)


@requests_bp.route('/asset-requests/<int:req_id>/cancel', methods=['POST'])
@login_required
def cancel_asset_request(req_id):
    req = AssetRequest.query.get_or_404(req_id)
    if req.requested_by_id != current_user.id and current_user.role != 'admin':
        abort(403)
    if req.status != 'pending':
        flash('Only pending requests can be cancelled.', 'error')
        return redirect(url_for('requests.asset_requests'))
    db.session.delete(req)
    db.session.commit()
    flash('Request cancelled.', 'success')
    return redirect(url_for('requests.asset_requests'))


# ─────────────────────────────────────────────
#  RETURN REQUESTS (return an assigned asset)
# ─────────────────────────────────────────────

@requests_bp.route('/return-requests')
@login_required
def return_requests():
    if current_user.role in ('admin', 'finance'):
        items = ReturnRequest.query.order_by(
            ReturnRequest.status.asc(),
            ReturnRequest.requested_at.desc()
        ).all()
    else:
        items = ReturnRequest.query.filter_by(requested_by_id=current_user.id)\
                                   .order_by(ReturnRequest.requested_at.desc()).all()
    return render_template('requests/return_requests.html', requests=items)


@requests_bp.route('/return-requests/new/<int:asset_id>', methods=['GET', 'POST'])
@login_required
def new_return_request(asset_id):
    asset = Asset.query.get_or_404(asset_id)
    if asset.assigned_to_id != current_user.id:
        abort(403)

    # Check no pending return request already exists for this asset
    existing = ReturnRequest.query.filter_by(
        asset_id=asset_id, requested_by_id=current_user.id, status='pending'
    ).first()
    if existing:
        flash('You already have a pending return request for this asset. Please wait for admin review.', 'warning')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        ret = ReturnRequest(
            asset_id            = asset.id,
            requested_by_id     = current_user.id,
            reason              = request.form.get('reason', '').strip(),
            condition_at_return = request.form.get('condition_at_return', 'good'),
            status              = 'pending',
        )
        db.session.add(ret)
        db.session.commit()
        flash('✓ Return request submitted. An administrator will review it shortly.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('requests/new_return_request.html', asset=asset)


@requests_bp.route('/return-requests/<int:req_id>/review', methods=['POST'])
@login_required
@admin_required
def review_return_request(req_id):
    ret    = ReturnRequest.query.get_or_404(req_id)
    action = request.form.get('action')  # approve | reject

    ret.reviewed_by_id = current_user.id
    ret.reviewed_at    = datetime.utcnow()
    ret.admin_note     = request.form.get('admin_note', '').strip()

    if action == 'approve':
        # Log the actual return record
        from models import ReturnRecord
        record = ReturnRecord(
            asset_id            = ret.asset_id,
            user_id             = ret.requested_by_id,
            condition_at_return = ret.condition_at_return,
            returned_at         = date.today(),
            notes               = ret.reason,
            processed_by_id     = current_user.id,
        )
        db.session.add(record)
        # Unassign asset and update condition
        asset = Asset.query.get(ret.asset_id)
        asset.condition      = ret.condition_at_return
        asset.assigned_to_id = None
        asset.assigned_on    = None
        ret.status = 'approved'
        db.session.commit()
        flash(f'✓ Return approved. {asset.tag} is now back in inventory.', 'success')

    elif action == 'reject':
        ret.status = 'rejected'
        db.session.commit()
        flash('Return request rejected. Asset remains assigned.', 'success')

    return redirect(url_for('requests.return_requests'))
