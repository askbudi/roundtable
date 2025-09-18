"""
GitHub API service for repository management
"""
import httpx
import json
from typing import Dict, Any, Optional
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors"""
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class GitHubService:
    """GitHub API service for repository operations"""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Clovable/1.0"
        }
    
    async def check_token_validity(self) -> Dict[str, Any]:
        """Check if the GitHub token is valid and get user info"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/user",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "valid": True,
                        "username": user_data.get("login"),
                        "name": user_data.get("name"),
                        "email": user_data.get("email"),
                        "avatar_url": user_data.get("avatar_url")
                    }
                elif response.status_code == 401:
                    return {"valid": False, "error": "Invalid or expired token"}
                else:
                    return {"valid": False, "error": f"GitHub API error: {response.status_code}"}
                    
            except Exception as e:
                logger.error(f"Error validating GitHub token: {e}")
                return {"valid": False, "error": str(e)}
    
    async def check_repository_exists(self, repo_name: str, username: str) -> bool:
        """Check if a repository exists for the authenticated user"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/repos/{username}/{repo_name}",
                    headers=self.headers
                )
                
                return response.status_code == 200
                
            except Exception as e:
                logger.error(f"Error checking repository existence: {e}")
                return False
    
    async def create_repository(
        self, 
        repo_name: str, 
        description: str = "", 
        private: bool = False,
        auto_init: bool = False
    ) -> Dict[str, Any]:
        """Create a new GitHub repository"""
        
        # Get user info first
        user_info = await self.check_token_validity()
        if not user_info.get("valid"):
            raise GitHubAPIError("Invalid GitHub token", 401)
        
        username = user_info["username"]
        
        # Check if repository already exists
        if await self.check_repository_exists(repo_name, username):
            raise GitHubAPIError(f"Repository '{repo_name}' already exists", 409)
        
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "name": repo_name,
                    "description": description,
                    "private": private,
                    "auto_init": auto_init,
                    "homepage": "",
                    "has_issues": True,
                    "has_projects": True,
                    "has_wiki": False,
                    "has_downloads": True
                }
                
                response = await client.post(
                    f"{self.BASE_URL}/user/repos",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 201:
                    repo_data = response.json()
                    return {
                        "success": True,
                        "repo_url": repo_data["html_url"],
                        "clone_url": repo_data["clone_url"],
                        "ssh_url": repo_data["ssh_url"],
                        "git_url": repo_data["git_url"],
                        "name": repo_data["name"],
                        "full_name": repo_data["full_name"],
                        "repo_id": repo_data["id"],
                        "private": repo_data["private"],
                        "default_branch": repo_data["default_branch"] or "main"
                    }
                elif response.status_code == 422:
                    error_data = response.json()
                    if "errors" in error_data:
                        error_msg = "; ".join([err.get("message", "Unknown error") for err in error_data["errors"]])
                    else:
                        error_msg = error_data.get("message", "Repository creation failed")
                    raise GitHubAPIError(f"Repository creation failed: {error_msg}", 422)
                elif response.status_code == 401:
                    raise GitHubAPIError("GitHub authentication failed", 401)
                elif response.status_code == 403:
                    raise GitHubAPIError("GitHub access denied. Check token permissions", 403)
                else:
                    error_text = response.text
                    raise GitHubAPIError(f"GitHub API error: {response.status_code} - {error_text}", response.status_code)
                    
            except GitHubAPIError:
                raise
            except Exception as e:
                logger.error(f"Error creating GitHub repository: {e}")
                raise GitHubAPIError(f"Failed to create repository: {str(e)}")
    
    async def get_repository_info(self, username: str, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get repository information including repository ID"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/repos/{username}/{repo_name}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    repo_data = response.json()
                    return {
                        "repo_url": repo_data["html_url"],
                        "clone_url": repo_data["clone_url"],
                        "ssh_url": repo_data["ssh_url"],
                        "git_url": repo_data["git_url"],
                        "name": repo_data["name"],
                        "full_name": repo_data["full_name"],
                        "repo_id": repo_data["id"],
                        "private": repo_data["private"],
                        "default_branch": repo_data["default_branch"] or "main"
                    }
                else:
                    return None
                    
            except Exception as e:
                logger.error(f"Error getting repository info: {e}")
                return None
    
    async def get_user_repositories(self, per_page: int = 30, page: int = 1) -> Dict[str, Any]:
        """Get user's repositories"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/user/repos",
                    headers=self.headers,
                    params={
                        "per_page": per_page,
                        "page": page,
                        "sort": "updated",
                        "direction": "desc"
                    }
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "repositories": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"GitHub API error: {response.status_code}"
                    }
                    
            except Exception as e:
                logger.error(f"Error getting user repositories: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }


# Utility functions
async def validate_github_token(token: str) -> Dict[str, Any]:
    """Validate a GitHub token and return user info"""
    github_service = GitHubService(token)
    return await github_service.check_token_validity()


async def check_repo_availability(token: str, repo_name: str) -> Dict[str, Any]:
    """Check if a repository name is available"""
    github_service = GitHubService(token)
    
    # First validate token and get username
    user_info = await github_service.check_token_validity()
    if not user_info.get("valid"):
        return {"available": False, "error": "Invalid GitHub token"}
    
    username = user_info["username"]
    exists = await github_service.check_repository_exists(repo_name, username)
    
    return {
        "available": not exists,
        "exists": exists,
        "username": username
    }


