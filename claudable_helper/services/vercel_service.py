"""
Vercel integration service for creating projects and deployments
"""
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

VERCEL_API_BASE = "https://api.vercel.com"


class VercelAPIError(Exception):
    """Custom exception for Vercel API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class VercelService:
    """Service class for Vercel API integration"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def check_token_validity(self) -> Dict[str, Any]:
        """Check if the Vercel token is valid and get user info"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{VERCEL_API_BASE}/v2/user",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        return {
                            "valid": True,
                            "user_id": user_data.get("id"),
                            "username": user_data.get("username"),
                            "name": user_data.get("name"),
                            "email": user_data.get("email")
                        }
                    elif response.status == 401:
                        return {"valid": False, "error": "Invalid Vercel token"}
                    else:
                        error_text = await response.text()
                        return {"valid": False, "error": f"API error: {error_text}"}
        except Exception as e:
            logger.error(f"Error checking Vercel token validity: {e}")
            return {"valid": False, "error": str(e)}
    
    async def create_project_with_github(
        self,
        project_name: str,
        github_repo: str,  # format: "username/repo-name"
        framework: str = "nextjs",
        team_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new Vercel project and link it to a GitHub repository"""
        
        try:
            # Prepare the request payload
            payload = {
                "name": project_name,
                "framework": framework,
                "gitRepository": {
                    "type": "github",
                    "repo": github_repo
                }
            }
            
            # Build the URL with optional team_id
            url = f"{VERCEL_API_BASE}/v11/projects"
            if team_id:
                url += f"?teamId={team_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=payload
                ) as response:
                    response_data = await response.json()
                    
                    if response.status == 200 or response.status == 201:
                        project = response_data
                        return {
                            "success": True,
                            "project_id": project.get("id"),
                            "project_name": project.get("name"),
                            "framework": project.get("framework"),
                            "git_repository": project.get("link", {}).get("repo"),
                            "created_at": project.get("createdAt"),
                            "project_url": f"https://vercel.com/{project.get('accountId')}/{project.get('name')}",
                            "raw_response": project
                        }
                    else:
                        error_msg = response_data.get("error", {}).get("message", "Unknown error")
                        logger.error(f"Failed to create Vercel project: {error_msg}")
                        raise VercelAPIError(f"Failed to create project: {error_msg}", response.status)
                        
        except aiohttp.ClientError as e:
            logger.error(f"Network error while creating Vercel project: {e}")
            raise VercelAPIError(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while creating Vercel project: {e}")
            raise VercelAPIError(f"Unexpected error: {str(e)}")
    
    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project information by ID"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{VERCEL_API_BASE}/v9/projects/{project_id}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get("error", {}).get("message", "Unknown error")
                        except:
                            error_msg = await response.text()
                        raise VercelAPIError(f"Failed to get project: {error_msg}", response.status)
        except VercelAPIError:
            raise
        except Exception as e:
            logger.error(f"Error getting Vercel project: {e}")
            raise VercelAPIError(f"Error getting project: {str(e)}")
    
    async def create_deployment(
        self,
        project_name: str,
        github_repo_id: int,
        branch: str = "main",
        framework: str = "nextjs"
    ) -> Dict[str, Any]:
        """Create a new deployment from GitHub repository using repository ID"""
        
        try:
            payload = {
                "name": project_name,
                "gitSource": {
                    "type": "github",
                    "repoId": github_repo_id,
                    "ref": f"refs/heads/{branch}"
                },
                "projectSettings": {
                    "framework": framework
                }
            }
            
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{VERCEL_API_BASE}/v13/deployments",
                    headers=self.headers,
                    json=payload
                ) as response:
                    response_data = await response.json()
                    
                    if response.status != 200 and response.status != 201:
                        logger.error(f"Vercel API error: {response_data}")
                    
                    if response.status == 200 or response.status == 201:
                        deployment = response_data
                        
                        # Extract best public URL
                        deployment_url = deployment.get("url")
                        # Try to get public alias if available
                        aliases = deployment.get("automaticAliases", [])
                        if aliases:
                            # Use the first automatic alias which is usually more public
                            deployment_url = aliases[0]
                        
                        return {
                            "success": True,
                            "deployment_id": deployment.get("id"),
                            "deployment_url": deployment_url,
                            "status": deployment.get("readyState"),  # QUEUED, BUILDING, READY, ERROR
                            "ready": deployment.get("readyState") == "READY",
                            "created_at": deployment.get("createdAt"),
                            "raw_response": deployment
                        }
                    else:
                        error_msg = response_data.get("error", {}).get("message", "Unknown error")
                        logger.error(f"Failed to create Vercel deployment: {error_msg}")
                        logger.error(f"Full error response: {response_data}")
                        raise VercelAPIError(f"Failed to create deployment: {error_msg}", response.status)
                        
        except Exception as e:
            logger.error(f"Error creating Vercel deployment: {e}")
            raise VercelAPIError(f"Error creating deployment: {str(e)}")
    
    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status by ID"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{VERCEL_API_BASE}/v13/deployments/{deployment_id}",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        deployment = await response.json()
                        
                        # Use aliasFinal, fallback to alias[0], then url
                        final_url = (deployment.get("aliasFinal") or 
                                   (deployment.get("alias")[0] if deployment.get("alias") else None) or 
                                   deployment.get("url"))
                        
                        return {
                            "id": deployment.get("id"),
                            "url": final_url,  # Use aliasFinal instead of url
                            "status": deployment.get("readyState"),
                            "created_at": deployment.get("createdAt"),
                            "ready": deployment.get("ready"),
                            "raw_response": deployment
                        }
                    else:
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get("error", {}).get("message", "Unknown error")
                        except:
                            error_msg = await response.text()
                        raise VercelAPIError(f"Failed to get deployment: {error_msg}", response.status)
        except Exception as e:
            logger.error(f"Error getting Vercel deployment: {e}")
            raise VercelAPIError(f"Error getting deployment: {str(e)}")


async def check_project_availability(access_token: str, project_name: str) -> Dict[str, Any]:
    """Check if a Vercel project name is available by listing projects"""
    service = VercelService(access_token)
    
    try:
        # Get list of projects and check if name exists
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{VERCEL_API_BASE}/v10/projects",
                headers=service.headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    projects = data.get("projects", [])
                    
                    # Check if project name already exists
                    for project in projects:
                        if project.get("name") == project_name:
                            return {"available": False, "exists": True}
                    
                    # Name is available
                    return {"available": True, "exists": False}
                else:
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    except:
                        error_msg = await response.text()
                    
                    if response.status == 401:
                        return {"available": False, "error": "Invalid Vercel token"}
                    else:
                        return {"available": False, "error": f"API error: {error_msg}"}
                        
    except Exception as e:
        logger.error(f"Error checking Vercel project availability: {e}")
        return {"available": False, "error": str(e)}


# 활성 배포 모니터링 태스크들을 추적하는 딕셔너리
active_monitoring_tasks: Dict[str, asyncio.Task] = {}


async def start_deployment_monitoring(
    project_id: str, 
    deployment_id: str, 
    vercel_token: str,
    db_session_factory
) -> None:
    """배포 모니터링 백그라운드 태스크 시작"""
    
    # 기존 모니터링이 있으면 취소
    if project_id in active_monitoring_tasks:
        active_monitoring_tasks[project_id].cancel()
    
    # 새 모니터링 태스크 시작
    task = asyncio.create_task(
        monitor_deployment_status(project_id, deployment_id, vercel_token, db_session_factory)
    )
    active_monitoring_tasks[project_id] = task
    
    logger.info(f"🚀 Started deployment monitoring for project {project_id}, deployment {deployment_id}")


async def monitor_deployment_status(
    project_id: str, 
    deployment_id: str, 
    vercel_token: str,
    db_session_factory
) -> None:
    """3초마다 Vercel API 호출해서 배포 상태 모니터링"""
    
    vercel_service = VercelService(vercel_token)
    start_time = datetime.utcnow()
    max_duration_minutes = 15  # 15분 제한
    
    try:
        while True:
            try:
                # 시간 제한 체크 (15분)
                elapsed = (datetime.utcnow() - start_time).total_seconds() / 60
                if elapsed > max_duration_minutes:
                    logger.warning(f"⏰ Deployment {deployment_id} monitoring timed out after {max_duration_minutes} minutes")
                    break
                
                # Vercel API에서 최신 상태 가져오기
                status_data = await vercel_service.get_deployment_status(deployment_id)
                
                # 상태 변경 시에만 또는 READY/ERROR 시에만 로그
                if status_data["status"] in ["READY", "ERROR"] or elapsed < 0.1:  # 처음 또는 완료 시에만
                    logger.info(f"🔍 Checking deployment {deployment_id} status... (elapsed: {elapsed:.1f}min)")
                    logger.info(f"🔍 Got status: {status_data['status']} for deployment {deployment_id}")
                
                # READY 상태일 때만 URL 정보 로그
                if status_data["status"] == "READY":
                    raw_response = status_data.get("raw_response", {})
                    logger.info(f"🎉 READY response - aliasFinal: {raw_response.get('aliasFinal')}, alias: {raw_response.get('alias', [])[:2]}, url: {raw_response.get('url')}")
                    logger.info(f"🎉 Final URL selected: {status_data['url']}")
                
                # DB 업데이트
                await update_deployment_status_in_db(project_id, status_data, db_session_factory)
                
                # 완료 상태 체크 - ready 필드도 확인
                is_ready = (status_data["status"] == "READY" or 
                           status_data.get("ready") == True or
                           status_data.get("readyState") == "READY")
                is_error = status_data["status"] == "ERROR"
                
                if is_ready or is_error:
                    logger.info(f"✅ Deployment {deployment_id} finished with status: {status_data['status']}")
                    break
                
                # 3초 대기
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Error monitoring deployment {deployment_id}: {e}")
                import traceback
                logger.error(f"❌ Full traceback: {traceback.format_exc()}")
                # 에러 시 10초 대기 후 재시도
                await asyncio.sleep(10)
                
    except asyncio.CancelledError:
        logger.info(f"Deployment monitoring cancelled for project {project_id}")
    except Exception as e:
        logger.error(f"Unexpected error in deployment monitoring: {e}")
    finally:
        # 모니터링 완료 시 태스크 목록에서 제거
        if project_id in active_monitoring_tasks:
            del active_monitoring_tasks[project_id]


async def update_deployment_status_in_db(
    project_id: str, 
    status_data: Dict[str, Any],
    db_session_factory
) -> None:
    """DB의 배포 상태 업데이트"""
    
    try:
        # DB 세션 생성 (비동기 환경에서 새 세션 필요)
        from sqlalchemy.orm import sessionmaker
        from ..models.project_services import ProjectServiceConnection
        
        Session = db_session_factory
        db = Session()
        
        try:
            # Vercel 연결 찾기
            connection = db.query(ProjectServiceConnection).filter(
                ProjectServiceConnection.project_id == project_id,
                ProjectServiceConnection.provider == "vercel"
            ).first()
            
            if connection:
                service_data = dict(connection.service_data) if connection.service_data else {}
                
                # current_deployment 정보 업데이트
                service_data["current_deployment"] = {
                    "deployment_id": status_data["id"],
                    "status": status_data["status"],
                    "deployment_url": status_data["url"],
                    "last_checked_at": datetime.utcnow().isoformat() + "Z"
                }
                
                # 배포 완료 시 deployment_url 메인에도 업데이트
                if status_data["status"] == "READY":
                    service_data["deployment_url"] = f"https://{status_data['url']}" if not str(status_data["url"]).startswith("http") else status_data["url"]
                    service_data["last_deployment_at"] = datetime.utcnow().isoformat() + "Z"
                    # 모니터링 완료 시 current_deployment 제거
                    service_data["current_deployment"] = None
                elif status_data["status"] == "ERROR":
                    # 에러 시에도 current_deployment 제거
                    service_data["current_deployment"] = None
                
                # 명시적으로 새 dict 할당
                connection.service_data = service_data
                db.commit()
                db.refresh(connection)
                
                # 검증: 실제로 저장되었는지 확인
                updated_data = connection.service_data or {}
                if "current_deployment" in updated_data:
                    if status_data["status"] == "READY":
                        logger.info(f"✅ Successfully saved READY deployment to DB for project {project_id}")
                        logger.info(f"📝 Final service_data keys: {list(updated_data.keys())}")
                else:
                    logger.error(f"❌ DB update verification failed for project {project_id}")
            else:
                logger.error(f"❌ No Vercel connection found for project {project_id}")
                
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Failed to update deployment status in DB: {e}")
        import traceback
        logger.error(f"❌ Full traceback: {traceback.format_exc()}")


def stop_deployment_monitoring(project_id: str) -> None:
    """특정 프로젝트의 배포 모니터링 중단"""
    if project_id in active_monitoring_tasks:
        active_monitoring_tasks[project_id].cancel()
        del active_monitoring_tasks[project_id]
        logger.info(f"Stopped deployment monitoring for project {project_id}")


def get_active_monitoring_projects() -> list:
    """현재 모니터링 중인 프로젝트 목록 반환"""
    return list(active_monitoring_tasks.keys())