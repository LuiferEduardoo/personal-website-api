from fastapi import APIRouter

from app.api.v1.endpoints import auth, blog_posts, health, images, projects, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(images.router)
api_router.include_router(blog_posts.router)
api_router.include_router(projects.router)
