"""
Settings API endpoints
Manage GitHub token and other configuration
"""
import os
from pathlib import Path
from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger('lazy-bird-api')

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')


def get_secrets_dir():
    """Get the secrets directory path"""
    return Path.home() / '.config' / 'lazy_birtd' / 'secrets'


def get_token_path():
    """Get the GitHub token file path"""
    return get_secrets_dir() / 'api_token'


@settings_bp.route('/token', methods=['GET'])
def get_token_status():
    """
    Get GitHub token status (masked)
    Returns whether a token exists and its first/last few characters
    """
    try:
        token_path = get_token_path()

        if not token_path.exists():
            return jsonify({
                'exists': False,
                'masked_token': None,
                'length': 0
            }), 200

        with open(token_path, 'r') as f:
            token = f.read().strip()

        # Mask token (show first 4 and last 4 chars)
        if len(token) > 8:
            masked = f"{token[:4]}...{token[-4:]}"
        else:
            masked = "***"

        return jsonify({
            'exists': True,
            'masked_token': masked,
            'length': len(token)
        }), 200

    except Exception as e:
        logger.error(f"Error reading token: {e}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/token', methods=['PUT'])
def update_token():
    """
    Update GitHub token

    Request body:
    {
        "token": "ghp_xxxxxxxxxxxx"
    }
    """
    try:
        data = request.get_json()

        if not data or 'token' not in data:
            return jsonify({'error': 'Token is required'}), 400

        token = data['token'].strip()

        if not token:
            return jsonify({'error': 'Token cannot be empty'}), 400

        # Validate token format (GitHub tokens start with ghp_, gho_, etc.)
        if not any(token.startswith(prefix) for prefix in ['ghp_', 'gho_', 'github_pat_']):
            return jsonify({
                'error': 'Invalid token format. GitHub tokens should start with ghp_, gho_, or github_pat_'
            }), 400

        # Create secrets directory if it doesn't exist
        secrets_dir = get_secrets_dir()
        secrets_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(secrets_dir, 0o700)

        # Write token to file
        token_path = get_token_path()
        with open(token_path, 'w') as f:
            f.write(token)

        # Set secure permissions
        os.chmod(token_path, 0o600)

        logger.info(f"GitHub token updated successfully")

        # Mask token for response
        if len(token) > 8:
            masked = f"{token[:4]}...{token[-4:]}"
        else:
            masked = "***"

        return jsonify({
            'success': True,
            'message': 'Token updated successfully',
            'masked_token': masked,
            'restart_required': True
        }), 200

    except Exception as e:
        logger.error(f"Error updating token: {e}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/token/test', methods=['POST'])
def test_token():
    """
    Test if the current GitHub token is valid
    """
    try:
        import requests

        token_path = get_token_path()

        if not token_path.exists():
            return jsonify({
                'valid': False,
                'error': 'No token found'
            }), 200

        with open(token_path, 'r') as f:
            token = f.read().strip()

        # Test token by making a request to GitHub API
        headers = {'Authorization': f'token {token}'}
        response = requests.get('https://api.github.com/user', headers=headers)

        if response.status_code == 200:
            user_data = response.json()
            return jsonify({
                'valid': True,
                'username': user_data.get('login'),
                'name': user_data.get('name'),
                'scopes': response.headers.get('X-OAuth-Scopes', '').split(', ')
            }), 200
        else:
            return jsonify({
                'valid': False,
                'error': 'Invalid or expired token',
                'status_code': response.status_code
            }), 200

    except Exception as e:
        logger.error(f"Error testing token: {e}")
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 500
