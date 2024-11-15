from unittest.mock import patch, MagicMock
from openhands_resolver.issue_definitions import IssueHandler, PRHandler
from openhands_resolver.github_issue import GithubIssue
from openhands.events.action.message import MessageAction
from openhands.core.config import LLMConfig

def test_get_converted_issues_initializes_review_comments():
    # Mock the necessary dependencies
    with patch('requests.get') as mock_get:
        # Mock the response for issues
        mock_issues_response = MagicMock()
        mock_issues_response.json.return_value = [{
            'number': 1,
            'title': 'Test Issue',
            'body': 'Test Body'
        }]
        # Mock the response for comments
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = []
        
        # Set up the mock to return different responses for different calls
        # First call is for issues, second call is for comments
        mock_get.side_effect = [mock_issues_response, mock_comments_response, mock_comments_response]  # Need two comment responses because we make two API calls
        
        # Create an instance of IssueHandler
        handler = IssueHandler('test-owner', 'test-repo', 'test-token')
        
        # Get converted issues
        issues = handler.get_converted_issues()
        
        # Verify that we got exactly one issue
        assert len(issues) == 1
        
        # Verify that review_comments is initialized as None
        assert issues[0].review_comments is None
        
        # Verify other fields are set correctly
        assert issues[0].number == 1
        assert issues[0].title == 'Test Issue'
        assert issues[0].body == 'Test Body'
        assert issues[0].owner == 'test-owner'
        assert issues[0].repo == 'test-repo'

def test_pr_handler_guess_success_with_thread_comments():
    # Create a PR handler instance
    handler = PRHandler('test-owner', 'test-repo', 'test-token')
    
    # Create a mock issue with thread comments but no review comments
    issue = GithubIssue(
        owner='test-owner',
        repo='test-repo',
        number=1,
        title='Test PR',
        body='Test Body',
        thread_comments=['First comment', 'Second comment'],
        closing_issues=['Issue description'],
        review_comments=None,
        thread_ids=None,
        head_branch='test-branch'
    )
    
    # Create mock history
    history = [MessageAction(content='Fixed the issue by implementing X and Y')]
    
    # Create mock LLM config
    llm_config = LLMConfig(model='test-model', api_key='test-key')
    
    # Mock the LLM response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="""--- success
true

--- explanation
The changes successfully address the feedback."""
            )
        )
    ]
    
    # Test the guess_success method
    with patch('litellm.completion', return_value=mock_response):
        success, success_list, explanation = handler.guess_success(issue, history, llm_config)
        
        # Verify the results
        assert success is True
        assert success_list == [True]
        assert "successfully address" in explanation

def test_pr_handler_get_converted_issues_with_comments():
    # Mock the necessary dependencies
    with patch('requests.get') as mock_get:
        # Mock the response for PRs
        mock_prs_response = MagicMock()
        mock_prs_response.json.return_value = [{
            'number': 1,
            'title': 'Test PR',
            'body': 'Test Body',
            'head': {'ref': 'test-branch'}
        }]
        
        # Mock the response for PR comments
        mock_comments_response = MagicMock()
        mock_comments_response.json.return_value = [
            {'body': 'First comment'},
            {'body': 'Second comment'}
        ]
        
        # Mock the response for PR metadata (GraphQL)
        mock_graphql_response = MagicMock()
        mock_graphql_response.json.return_value = {
            'data': {
                'repository': {
                    'pullRequest': {
                        'closingIssuesReferences': {'edges': []},
                        'reviews': {'nodes': []},
                        'reviewThreads': {'edges': []}
                    }
                }
            }
        }
        
        # Set up the mock to return different responses
        # We need to return empty responses for subsequent pages
        mock_empty_response = MagicMock()
        mock_empty_response.json.return_value = []
        
        mock_get.side_effect = [
            mock_prs_response,  # First call for PRs
            mock_empty_response,  # Second call for PRs (empty page)
            mock_comments_response,  # Third call for PR comments
            mock_empty_response,  # Fourth call for PR comments (empty page)
        ]
        
        # Mock the post request for GraphQL
        with patch('requests.post') as mock_post:
            mock_post.return_value = mock_graphql_response
            
            # Create an instance of PRHandler
            handler = PRHandler('test-owner', 'test-repo', 'test-token')
            
            # Get converted issues
            prs = handler.get_converted_issues()
            
            # Verify that we got exactly one PR
            assert len(prs) == 1
            
            # Verify that thread_comments are set correctly
            assert prs[0].thread_comments == ['First comment', 'Second comment']
            
            # Verify other fields are set correctly
            assert prs[0].number == 1
            assert prs[0].title == 'Test PR'
            assert prs[0].body == 'Test Body'
            assert prs[0].owner == 'test-owner'
            assert prs[0].repo == 'test-repo'
            assert prs[0].head_branch == 'test-branch'

def test_pr_handler_guess_success_only_review_comments():
    # Create a PR handler instance
    handler = PRHandler('test-owner', 'test-repo', 'test-token')
    
    # Create a mock issue with only review comments
    issue = GithubIssue(
        owner='test-owner',
        repo='test-repo',
        number=1,
        title='Test PR',
        body='Test Body',
        thread_comments=None,
        closing_issues=['Issue description'],
        review_comments=['Please fix the formatting', 'Add more tests'],
        thread_ids=None,
        head_branch='test-branch'
    )
    
    # Create mock history
    history = [MessageAction(content='Fixed the formatting and added more tests')]
    
    # Create mock LLM config
    llm_config = LLMConfig(model='test-model', api_key='test-key')
    
    # Mock the LLM response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="""--- success
true

--- explanation
The changes successfully address the review comments."""
            )
        )
    ]
    
    # Test the guess_success method
    with patch('litellm.completion', return_value=mock_response):
        success, success_list, explanation = handler.guess_success(issue, history, llm_config)
        
        # Verify the results
        assert success is True
        assert success_list == [True]
        assert "successfully address" in explanation

def test_pr_handler_guess_success_no_comments():
    # Create a PR handler instance
    handler = PRHandler('test-owner', 'test-repo', 'test-token')
    
    # Create a mock issue with no comments
    issue = GithubIssue(
        owner='test-owner',
        repo='test-repo',
        number=1,
        title='Test PR',
        body='Test Body',
        thread_comments=None,
        closing_issues=['Issue description'],
        review_comments=None,
        thread_ids=None,
        head_branch='test-branch'
    )
    
    # Create mock history
    history = [MessageAction(content='Fixed the issue')]
    
    # Create mock LLM config
    llm_config = LLMConfig(model='test-model', api_key='test-key')
    
    # Test that it returns appropriate message when no comments are present
    success, success_list, explanation = handler.guess_success(issue, history, llm_config)
    assert success is False
    assert success_list is None
    assert explanation == "No feedback was found to process"
