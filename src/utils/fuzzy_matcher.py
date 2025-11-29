"""
Fuzzy matching utility for task descriptions with Hebrew and English support.
Handles typos and variations in user input when searching for tasks.
"""
from rapidfuzz import fuzz, process
from typing import List, Tuple, Optional, Any
from datetime import datetime, timedelta
import pytz


class FuzzyTaskMatcher:
    """
    Fuzzy matching for task descriptions with typo tolerance.
    
    Features:
    - Handles typos in Hebrew and English
    - Similarity scoring (0-100)
    - Smart task selection by similarity + due date
    - Configurable thresholds
    
    Usage:
        matcher = FuzzyTaskMatcher()
        task, score = matcher.find_single_best_match("לקנות חלבב", tasks)
    """
    
    # Configurable thresholds (tune based on user feedback)
    MIN_SIMILARITY_THRESHOLD = 60  # Minimum score to consider a match
    GOOD_MATCH_THRESHOLD = 80      # Considered a "good" confident match
    EXCELLENT_MATCH_THRESHOLD = 90 # Almost perfect match
    
    def __init__(self, israel_tz=None):
        """
        Initialize matcher with timezone.
        
        Args:
            israel_tz: pytz timezone object (default: Asia/Jerusalem)
        """
        self.israel_tz = israel_tz or pytz.timezone('Asia/Jerusalem')
    
    def find_best_matches(self, search_term: str, tasks: List[Any], top_n: int = 5) -> List[Tuple[Any, float]]:
        """
        Find best matching tasks using fuzzy string matching.
        
        Args:
            search_term: The text user typed (possibly with typos)
            tasks: List of Task objects to search through
            top_n: Maximum number of matches to return
            
        Returns:
            List of (task, similarity_score) tuples, sorted by score descending
            
        Example:
            >>> matches = matcher.find_best_matches("לקנות חלבב", tasks, top_n=3)
            >>> [(task1, 95.0), (task2, 87.5), (task3, 72.0)]
        """
        if not tasks or not search_term:
            return []
        
        # Extract descriptions and task objects
        choices = [(task.description, task) for task in tasks]
        
        # Use rapidfuzz to find best matches
        # token_set_ratio is ideal for:
        # - Word order variations ("buy milk" vs "milk buy")
        # - Partial matches ("buy" matches "buy milk")
        # - Multiple languages (Hebrew/English)
        # - Typo tolerance
        matches = process.extract(
            search_term,
            choices,
            scorer=fuzz.partial_ratio,
            limit=top_n,
            score_cutoff=self.MIN_SIMILARITY_THRESHOLD
        )
        
        # Convert from rapidfuzz format to our format
        # matches is list of: (matched_string, score, (description, task_object))
        results = []
        for match in matches:
            matched_desc, score, (_, task_obj) = match
            results.append((task_obj, score))
        
        return results
    
    def find_single_best_match(self, search_term: str, tasks: List[Any]) -> Optional[Tuple[Any, float]]:
        """
        Find single best matching task with smart tiebreaking.
        
        Matching strategy:
        1. Find tasks above similarity threshold
        2. If multiple tasks have similar scores, use due date as tiebreaker
        3. Prioritize: overdue > upcoming > no due date
        
        Args:
            search_term: The text user typed
            tasks: List of Task objects
            
        Returns:
            (task, similarity_score) or None if no good match
            
        Example:
            >>> task, score = matcher.find_single_best_match("לקנות חלבב", tasks)
            >>> print(f"Matched: {task.description} (score: {score})")
            "Matched: לקנות חלב (score: 95.0)"
        """
        matches = self.find_best_matches(search_term, tasks, top_n=10)
        
        if not matches:
            return None
        
        # Get the best score
        best_score = matches[0][1]
        
        # Find all tasks with the best score (or within 2 points - floating point tolerance)
        top_matches = [(task, score) for task, score in matches if score >= best_score - 2]
        
        if len(top_matches) == 1:
            # Single clear winner
            return top_matches[0]
        
        # Multiple tasks with similar scores - use due date as tiebreaker
        print(f"🔍 Fuzzy match: Multiple tasks with similar scores, using due date tiebreaker")
        best_task = self._select_by_due_date([task for task, _ in top_matches])
        
        if best_task:
            # Find the score for this task
            score = next((s for t, s in top_matches if t.id == best_task.id), best_score)
            return (best_task, score)
        
        # Fallback to first match
        return top_matches[0]
    
    def _select_by_due_date(self, tasks: List[Any]) -> Optional[Any]:
        """
        Select best task from multiple matches based on due date priority.
        
        Priority order:
        1. Tasks overdue (earliest date = most overdue)
        2. Tasks due today (earliest time)
        3. Tasks upcoming (soonest first)
        4. Tasks without due date (lowest priority)
        
        Args:
            tasks: List of Task objects
            
        Returns:
            Single Task object or None
        """
        if not tasks:
            return None
        
        if len(tasks) == 1:
            return tasks[0]
        
        # Calculate "today" in Israel timezone
        now_israel = datetime.now(self.israel_tz)
        today_start = now_israel.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(hour=23, minute=59, second=59)
        
        # Convert to UTC for comparison (database stores in UTC)
        today_start_utc = today_start.astimezone(pytz.UTC).replace(tzinfo=None)
        today_end_utc = today_end.astimezone(pytz.UTC).replace(tzinfo=None)
        
        # Categorize tasks
        overdue_tasks = []
        today_tasks = []
        upcoming_tasks = []
        no_date_tasks = []
        
        for task in tasks:
            if task.due_date:
                # Ensure due_date is offset-naive UTC for comparison
                task_due = task.due_date
                if task_due.tzinfo:
                     task_due = task_due.astimezone(pytz.UTC).replace(tzinfo=None)
                
                if task_due < today_start_utc:
                    overdue_tasks.append(task)
                elif task_due <= today_end_utc:
                    today_tasks.append(task)
                else:
                    upcoming_tasks.append(task)
            else:
                no_date_tasks.append(task)
        
        # Return based on priority
        if overdue_tasks:
            # Most overdue = earliest date
            return min(overdue_tasks, key=lambda t: t.due_date)
        elif today_tasks:
            # Earliest today
            return min(today_tasks, key=lambda t: t.due_date)
        elif upcoming_tasks:
            # Soonest upcoming
            return min(upcoming_tasks, key=lambda t: t.due_date)
        elif no_date_tasks:
            # Just pick first one
            return no_date_tasks[0]
        
        return tasks[0]  # Ultimate fallback
    
    def get_similarity_score(self, search_term: str, task_description: str) -> float:
        """
        Calculate similarity score between search term and task description.
        
        Args:
            search_term: User's input
            task_description: Task description to compare
            
        Returns:
            Score from 0-100 (100 = perfect match, 0 = no similarity)
            
        Example:
            >>> score = matcher.get_similarity_score("לקנות חלב", "לקנות חלבב")
            >>> print(score)
            95.0
        """
        return fuzz.partial_ratio(search_term, task_description)
    
    def is_good_match(self, score: float) -> bool:
        """
        Check if similarity score is considered a good match.
        
        Args:
            score: Similarity score (0-100)
            
        Returns:
            True if score >= GOOD_MATCH_THRESHOLD
        """
        return score >= self.GOOD_MATCH_THRESHOLD
    
    def is_excellent_match(self, score: float) -> bool:
        """
        Check if similarity score is considered an excellent match.
        
        Args:
            score: Similarity score (0-100)
            
        Returns:
            True if score >= EXCELLENT_MATCH_THRESHOLD
        """
        return score >= self.EXCELLENT_MATCH_THRESHOLD
    
    def get_match_quality_label(self, score: float) -> str:
        """
        Get human-readable label for match quality.
        
        Args:
            score: Similarity score (0-100)
            
        Returns:
            Hebrew label describing match quality
        """
        if score >= self.EXCELLENT_MATCH_THRESHOLD:
            return "התאמה מעולה"
        elif score >= self.GOOD_MATCH_THRESHOLD:
            return "התאמה טובה"
        elif score >= self.MIN_SIMILARITY_THRESHOLD:
            return "התאמה סבירה"
        else:
            return "התאמה חלשה"

