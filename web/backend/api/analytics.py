"""
Analytics API
Handles analytics and metrics endpoints
"""
from flask import Blueprint, request, jsonify
import logging
from services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')
analytics_service = AnalyticsService()


@analytics_bp.route('/overall', methods=['GET'])
def get_overall_analytics():
    """
    Get overall system analytics

    Query params:
        range: Time range (7d, 30d, 90d, all) - default: 7d

    Returns:
        200: Analytics data
        400: Invalid time range
        500: Server error
    """
    try:
        time_range = request.args.get('range', '7d')

        # Validate time range
        valid_ranges = ['7d', '30d', '90d', 'all']
        if time_range not in valid_ranges:
            return jsonify({
                'error': f'Invalid time range. Must be one of: {", ".join(valid_ranges)}'
            }), 400

        analytics = analytics_service.get_overall_analytics(time_range)
        return jsonify(analytics), 200

    except Exception as e:
        logger.error(f"Error getting overall analytics: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/project/<project_id>', methods=['GET'])
def get_project_analytics(project_id):
    """
    Get project-specific analytics

    Args:
        project_id: Project ID

    Query params:
        range: Time range (7d, 30d, 90d, all) - default: 30d

    Returns:
        200: Project analytics data
        400: Invalid time range
        500: Server error
    """
    try:
        time_range = request.args.get('range', '30d')

        # Validate time range
        valid_ranges = ['7d', '30d', '90d', 'all']
        if time_range not in valid_ranges:
            return jsonify({
                'error': f'Invalid time range. Must be one of: {", ".join(valid_ranges)}'
            }), 400

        analytics = analytics_service.get_project_analytics(project_id, time_range)
        return jsonify(analytics), 200

    except Exception as e:
        logger.error(f"Error getting project analytics for {project_id}: {e}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/costs', methods=['GET'])
def get_cost_analytics():
    """
    Get cost analytics

    Note: For Phase 1.1, this returns placeholder data.
    Real cost tracking will be implemented in future phases.

    Returns:
        200: Cost analytics data
        500: Server error
    """
    try:
        cost_data = analytics_service.get_cost_analytics()
        return jsonify(cost_data), 200

    except Exception as e:
        logger.error(f"Error getting cost analytics: {e}")
        return jsonify({'error': str(e)}), 500
