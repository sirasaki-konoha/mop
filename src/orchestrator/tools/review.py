"""
review_code tool implementation for Multi-Agent MCP Orchestrator.

This module implements the review_code tool that allows Agent C (Tester)
to review artifacts submitted by other agents.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from ..models.artifact import Artifact
from ..storage.artifact_store import ArtifactStore


class ReviewStatus(Enum):
    """Status of a code review."""
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


@dataclass
class ReviewComment:
    """A single review comment."""
    line_number: Optional[int]
    comment: str
    severity: str  # "info", "warning", "error"


@dataclass
class Review:
    """Result of a code review."""
    artifact_id: str
    reviewer_agent_id: str
    status: ReviewStatus
    comments: List[ReviewComment]
    suggestions: List[str]
    timestamp: datetime
    
    def to_dict(self) -> dict:
        """Convert review to dictionary for serialization."""
        return {
            "artifact_id": self.artifact_id,
            "reviewer_agent_id": self.reviewer_agent_id,
            "status": self.status.value,
            "comments": [
                {
                    "line_number": c.line_number,
                    "comment": c.comment,
                    "severity": c.severity
                }
                for c in self.comments
            ],
            "suggestions": self.suggestions,
            "timestamp": self.timestamp.isoformat()
        }


class ReviewTool:
    """
    Tool for reviewing code artifacts.
    
    This tool implements the review_code functionality as specified in the
    Multi-Agent MCP Orchestrator design document.
    """
    
    def __init__(self, artifact_store: ArtifactStore):
        """
        Initialize the review tool.
        
        Args:
            artifact_store: Store for accessing artifacts to review
        """
        self.artifact_store = artifact_store
    
    async def review_code(self, artifact_id: str, reviewer_agent_id: str) -> Review:
        """
        Review a code artifact.
        
        Args:
            artifact_id: ID of the artifact to review
            reviewer_agent_id: ID of the agent performing the review
            
        Returns:
            Review object with comments, status, and suggestions
            
        Raises:
            ValueError: If artifact not found
        """
        # Retrieve the artifact from store
        artifact = await self.artifact_store.get_artifact(artifact_id)
        if artifact is None:
            raise ValueError(f"Artifact not found: {artifact_id}")
        
        # Perform the review based on artifact type
        if artifact.type == "code":
            review_result = await self._review_code_artifact(artifact)
        elif artifact.type == "test":
            review_result = await self._review_test_artifact(artifact)
        elif artifact.type == "doc":
            review_result = await self._review_documentation_artifact(artifact)
        else:
            review_result = await self._review_generic_artifact(artifact)
        
        # Create and return the review
        return Review(
            artifact_id=artifact_id,
            reviewer_agent_id=reviewer_agent_id,
            status=review_result["status"],
            comments=review_result["comments"],
            suggestions=review_result["suggestions"],
            timestamp=datetime.now()
        )
    
    async def _review_code_artifact(self, artifact: Artifact) -> dict:
        """
        Review a code artifact for quality and correctness.
        
        Args:
            artifact: The code artifact to review
            
        Returns:
            Dictionary with review results
        """
        comments = []
        suggestions = []
        
        # Check for basic code quality indicators
        lines = artifact.content.split('\n')
        
        # Check for type hints
        has_type_hints = False
        for line in lines:
            if 'def ' in line and '->' in line:
                has_type_hints = True
                break
        
        if not has_type_hints:
            comments.append(ReviewComment(
                line_number=None,
                comment="Missing type hints in function signatures",
                severity="warning"
            ))
            suggestions.append("Add type hints to improve code readability and maintainability")
        
        # Check for error handling
        has_error_handling = False
        for line in lines:
            if 'try:' in line or 'except' in line:
                has_error_handling = True
                break
        
        if not has_error_handling:
            comments.append(ReviewComment(
                line_number=None,
                comment="No error handling found in the code",
                severity="warning"
            ))
            suggestions.append("Add appropriate error handling for robustness")
        
        # Check for logging
        has_logging = False
        for line in lines:
            if 'logging' in line or 'logger' in line:
                has_logging = True
                break
        
        if not has_logging:
            comments.append(ReviewComment(
                line_number=None,
                comment="No logging found in the code",
                severity="info"
            ))
            suggestions.append("Add logging for better observability")
        
        # Determine overall status
        if any(c.severity == "error" for c in comments):
            status = ReviewStatus.REJECTED
        elif any(c.severity == "warning" for c in comments):
            status = ReviewStatus.CHANGES_REQUESTED
        else:
            status = ReviewStatus.APPROVED
        
        return {
            "status": status,
            "comments": comments,
            "suggestions": suggestions
        }
    
    async def _review_test_artifact(self, artifact: Artifact) -> dict:
        """
        Review a test artifact for coverage and quality.
        
        Args:
            artifact: The test artifact to review
            
        Returns:
            Dictionary with review results
        """
        comments = []
        suggestions = []
        
        lines = artifact.content.split('\n')
        
        # Check for test functions
        test_functions = [line for line in lines if line.strip().startswith('def test_')]
        if not test_functions:
            comments.append(ReviewComment(
                line_number=None,
                comment="No test functions found",
                severity="error"
            ))
            suggestions.append("Add test functions to verify functionality")
        
        # Check for assertions
        has_assertions = False
        for line in lines:
            if 'assert' in line:
                has_assertions = True
                break
        
        if not has_assertions:
            comments.append(ReviewComment(
                line_number=None,
                comment="No assertions found in tests",
                severity="error"
            ))
            suggestions.append("Add assertions to verify expected behavior")
        
        # Determine status
        if any(c.severity == "error" for c in comments):
            status = ReviewStatus.REJECTED
        elif any(c.severity == "warning" for c in comments):
            status = ReviewStatus.CHANGES_REQUESTED
        else:
            status = ReviewStatus.APPROVED
        
        return {
            "status": status,
            "comments": comments,
            "suggestions": suggestions
        }
    
    async def _review_documentation_artifact(self, artifact: Artifact) -> dict:
        """
        Review a documentation artifact.
        
        Args:
            artifact: The documentation artifact to review
            
        Returns:
            Dictionary with review results
        """
        comments = []
        suggestions = []
        
        # Check for basic documentation structure
        if len(artifact.content.strip()) < 50:
            comments.append(ReviewComment(
                line_number=None,
                comment="Documentation appears too brief",
                severity="warning"
            ))
            suggestions.append("Expand documentation with more details and examples")
        
        # Determine status
        if any(c.severity == "error" for c in comments):
            status = ReviewStatus.REJECTED
        elif any(c.severity == "warning" for c in comments):
            status = ReviewStatus.CHANGES_REQUESTED
        else:
            status = ReviewStatus.APPROVED
        
        return {
            "status": status,
            "comments": comments,
            "suggestions": suggestions
        }
    
    async def _review_generic_artifact(self, artifact: Artifact) -> dict:
        """
        Review a generic artifact.
        
        Args:
            artifact: The artifact to review
            
        Returns:
            Dictionary with review results
        """
        # For generic artifacts, just approve with no comments
        return {
            "status": ReviewStatus.APPROVED,
            "comments": [],
            "suggestions": []
        }