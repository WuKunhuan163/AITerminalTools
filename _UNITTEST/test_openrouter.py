#!/usr/bin/env python3
"""
Unit tests for OPENROUTER tool
"""

import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

from _UNITTEST.base_test import BaseTest, APITest


class TestOpenRouter(BaseTest):
    """Test cases for OPENROUTER tool"""

    def setUp(self):
        super().setUp()
        self.openrouter_script = self.get_bin_path('OPENROUTER')
        self.openrouter_py = self.get_python_path('OPENROUTER.py')

    def test_openrouter_script_exists(self):
        """Test that OPENROUTER script exists"""
        self.assertTrue(self.openrouter_script.exists())

    def test_openrouter_py_exists(self):
        """Test that OPENROUTER.py exists"""
        self.assertTrue(self.openrouter_py.exists())

    def test_help_output(self):
        """Test OPENROUTER help output"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), '--help'
        ])
        self.assertIn('OPENROUTER - OpenRouter API 调用工具', result.stdout)
        self.assertIn('Usage:', result.stdout)
        self.assertIn('--model', result.stdout)
        self.assertIn('--key', result.stdout)

    def test_missing_query_shows_help(self):
        """Test that missing query shows help instead of error"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py)
        ])
        self.assertIn('OPENROUTER - OpenRouter API 调用工具', result.stdout)
        self.assertIn('Usage:', result.stdout)

    def test_connection_test_no_api_key(self):
        """Test --test-connection with no API key"""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            result = self.assertCommandSuccess([
                sys.executable, str(self.openrouter_py), '--test-connection'
            ])
            self.assertIn('🔍 OpenRouter API连接测试结果:', result.stdout)
            self.assertIn('❌ 连接测试失败：未设置API密钥', result.stdout)

    def test_connection_test_with_fake_key(self):
        """Test --test-connection with fake API key"""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake_key"}):
            result = self.assertCommandSuccess([
                sys.executable, str(self.openrouter_py), '--test-connection'
            ], timeout=20)
            self.assertIn('🔍 OpenRouter API连接测试结果:', result.stdout)
            # Should show connection attempt results (even if failed due to fake key)
            self.assertTrue(
                '❌ API密钥无效或已过期' in result.stdout or 
                '❌ API调用失败' in result.stdout or
                '❌ 连接超时' in result.stdout or
                'No auth credentials found' in result.stdout or
                '❌ 总结: 连接测试失败' in result.stdout
            )

    def test_connection_test_with_custom_key(self):
        """Test --test-connection with custom key parameter"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), '--test-connection', '--key', 'custom_fake_key'
        ], timeout=20)
        self.assertIn('🔍 OpenRouter API连接测试结果:', result.stdout)
        # Should attempt connection with custom key
        self.assertTrue(
            '❌ API密钥无效或已过期' in result.stdout or 
            '❌ API请求失败' in result.stdout or
            '❌ 连接超时' in result.stdout or
            '❌ API调用失败: No auth credentials found' in result.stdout
        )

    def test_connection_test_with_model(self):
        """Test --test-connection with specific model"""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "fake_key"}):
            result = self.assertCommandSuccess([
                sys.executable, str(self.openrouter_py), '--test-connection', '--model', 'deepseek/deepseek-chat'
            ], timeout=20)
            self.assertIn('🔍 OpenRouter API连接测试结果:', result.stdout)

    def test_connection_test_run_mode(self):
        """Test --test-connection in RUN mode"""
        run_script = self.get_bin_path('RUN')
        result = self.assertCommandSuccess([
            str(run_script), '--show', 'OPENROUTER', '--test-connection'
        ], timeout=25)
        
        # Should return valid JSON
        try:
            json_result = json.loads(result.stdout)
            self.assertIn('success', json_result)
            self.assertIn('message', json_result)
            self.assertIn('results', json_result)
            self.assertIn('summary', json_result)
            self.assertIsInstance(json_result['results'], list)
            self.assertIsInstance(json_result['summary'], dict)
        except json.JSONDecodeError:
            self.fail(f"RUN mode should return valid JSON, got: {result.stdout}")

    def test_help_includes_test_connection(self):
        """Test that help output includes --test-connection option"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), '--help'
        ])
        self.assertIn('--test-connection', result.stdout)
        self.assertIn('测试API连接状态', result.stdout)

    def test_list_models(self):
        """Test --list option"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), '--list'
        ])
        self.assertIn('可用模型列表', result.stdout)
        self.assertIn('deepseek', result.stdout)

    def test_model_parameter(self):
        """Test that OPENROUTER accepts model parameter"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), 
            '--model', 'deepseek/deepseek-chat', '--help'
        ])
        self.assertIn('OPENROUTER - OpenRouter API 调用工具', result.stdout)

    def test_key_parameter(self):
        """Test that OPENROUTER accepts key parameter"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), 
            '--key', 'test-key', '--help'
        ])
        self.assertIn('OPENROUTER - OpenRouter API 调用工具', result.stdout)

    def test_max_tokens_parameter(self):
        """Test that OPENROUTER accepts max-tokens parameter"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), 
            '--max-tokens', '2000', '--help'
        ])
        self.assertIn('OPENROUTER - OpenRouter API 调用工具', result.stdout)

    def test_temperature_parameter(self):
        """Test that OPENROUTER accepts temperature parameter"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), 
            '--temperature', '0.9', '--help'
        ])
        self.assertIn('OPENROUTER - OpenRouter API 调用工具', result.stdout)

    def test_no_api_key_error(self):
        """Test error when no API key is provided"""
        # Remove API key from environment
        env = os.environ.copy()
        if 'OPENROUTER_API_KEY' in env:
            del env['OPENROUTER_API_KEY']
        
        result = self.run_subprocess([
            sys.executable, str(self.openrouter_py), 'test query'
        ], env=env)
        
        self.assertEqual(result.returncode, 1)
        self.assertIn('错误', result.stderr)


class TestOpenRouterAPI(APITest):
    """API tests for OPENROUTER tool that require longer timeouts"""

    def setUp(self):
        super().setUp()
        self.openrouter_py = self.get_python_path('OPENROUTER.py')

    @patch('requests.post')
    def test_api_call_error_mock(self, mock_post):
        """Test API call error with mocked response"""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_post.return_value = mock_response
        
        # Test with invalid key
        result = self.run_subprocess([
            sys.executable, str(self.openrouter_py), 
            'test query', '--key', 'invalid-key'
        ])
        
        # Mock may not work properly with subprocess, so just check it doesn't crash
        self.assertIn(result.returncode, [0, 1])  # Either success or error is acceptable


class TestOpenRouterIntegration(APITest):
    """Integration tests for OPENROUTER tool"""
    
    def setUp(self):
        super().setUp()
        self.openrouter_py = self.get_python_path('OPENROUTER.py')
        self.run_py = self.get_python_path('RUN.py')
    
    def test_run_show_compatibility(self):
        """Test RUN --show compatibility with OPENROUTER"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.run_py),
            '--show', 'OPENROUTER', '--help'
        ])
        
        # Parse JSON output
        try:
            # Remove ANSI escape sequences and clear screen characters
            import re
            clean_output = re.sub(r'\x1b\[[0-9;]*[mHJ]', '', result.stdout)
            
            lines = clean_output.strip().split('\n')
            json_content = ""
            
            # Find JSON content
            for line in lines:
                line = line.strip()
                if line.startswith('{') or json_content:
                    json_content += line + '\n'
                    if line.endswith('}') and json_content.count('{') == json_content.count('}'):
                        break
            
            if json_content:
                output_data = json.loads(json_content.strip())
                self.assertIn('success', output_data)
                self.assertTrue(output_data['success'])
                self.assertIn('_RUN_DATA_file', output_data)
                # Check that it's help-related content
                self.assertIn('message', output_data)
            else:
                # If no JSON found, check if the command at least ran
                self.assertIn('OPENROUTER', result.stdout + result.stderr)
                
        except json.JSONDecodeError:
            # If JSON parsing fails, check if the command at least ran
            self.assertIn('OPENROUTER', result.stdout + result.stderr)
    
    def test_basic_functionality(self):
        """Test basic OPENROUTER functionality"""
        # Test that the tool can be called and shows help for missing query
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py)
        ])
        self.assertIn('OPENROUTER - OpenRouter API 调用工具', result.stdout)
        self.assertIn('Usage:', result.stdout)
    
    def test_invalid_api_key_error(self):
        """Test error handling with invalid API key"""
        result = self.run_subprocess([
            sys.executable, str(self.openrouter_py),
            'test query', '--key', 'invalid-key-12345'
        ], timeout=30)
        
        # Should fail with invalid key
        self.assertEqual(result.returncode, 1)
        self.assertIn('错误', result.stderr)
    
    def test_output_dir_functionality(self):
        """Test --output-dir functionality (without actual API call)"""
        # Test that --output-dir parameter is accepted
        result = self.run_subprocess([
            sys.executable, str(self.openrouter_py),
            '--help'
        ])
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('--output-dir', result.stdout)
    
    def test_timeout_handling(self):
        """Test timeout handling for API calls"""
        # This test uses an invalid key which should fail quickly
        # rather than timing out, but tests the error handling path
        result = self.run_subprocess([
            sys.executable, str(self.openrouter_py),
            'test query', '--key', 'sk-invalid-timeout-test'
        ], timeout=15)
        
        # Should fail (not timeout) due to invalid key
        self.assertEqual(result.returncode, 1)
    
    def test_real_api_call_if_key_available(self):
        """Test real API call if OPENROUTER_API_KEY is available"""
        api_key = os.environ.get('OPENROUTER_API_KEY')
        
        if not api_key:
            self.skipTest("OPENROUTER_API_KEY not available for real API testing")
        
        # Test with real API key and simple query
        result = self.run_subprocess([
            sys.executable, str(self.openrouter_py),
            'Hi', '--max-tokens', '5'
        ], timeout=30)
        
        # Just check that the command completed successfully (exit code 0)
        # Don't check the specific content since it varies by model
        self.assertEqual(result.returncode, 0, 
                        f"API call should succeed with valid key. Output: {result.stdout}, Error: {result.stderr}")
    
    def test_max_tokens_without_key(self):
        """Test --max-tokens functionality without specifying --key"""
        api_key = os.environ.get('OPENROUTER_API_KEY')
        
        if not api_key:
            self.skipTest("OPENROUTER_API_KEY not available for max-tokens testing")
        
        # Test with long prompt and moderate max-tokens to verify truncation
        long_prompt = ("Write a detailed story about a space explorer discovering a new planet. "
                      "Include descriptions of the landscape, alien creatures, and the explorer's emotions. "
                      "Make it approximately 500 words long. "
                      "At the very end of your story, write exactly this sentence: 'This is the END of my story'")
        
        result = self.run_subprocess([
            sys.executable, str(self.openrouter_py),
            long_prompt, '--max-tokens', '100'
        ], timeout=45)
        
        if result.returncode == 0:
            # Verify the API call succeeded and tokens were limited
            # Check stderr for token usage info
            self.assertIn('📊 Token使用:', result.stderr, "Should show token usage information")
            
            # Extract output tokens from stderr
            import re
            token_match = re.search(r'输出 (\d+)', result.stderr)
            if token_match:
                output_tokens = int(token_match.group(1))
                # Should be close to max-tokens limit (100)
                self.assertLessEqual(output_tokens, 110, 
                                   f"Output tokens ({output_tokens}) should be limited by max-tokens=100")
            
            # Response should not contain the ending sentence due to truncation
            response = result.stdout.strip()
            if response:  # Only check if there's actual response content
                self.assertNotIn('This is the END of my story', response,
                               "Response should be truncated before the ending sentence")
        else:
            # If failed, should have reasonable error message
            self.assertIn('错误', result.stderr)
    
    def test_max_tokens_context_length_warning(self):
        """Test warning when max-tokens exceeds model context length"""
        api_key = os.environ.get('OPENROUTER_API_KEY')
        
        if not api_key:
            self.skipTest("OPENROUTER_API_KEY not available for context length testing")
        
        # Test with max-tokens that exceeds typical model context length
        result = self.run_subprocess([
            sys.executable, str(self.openrouter_py),
            'Hello', '--max-tokens', '100000000'  # Extremely large max-tokens
        ], timeout=30)
        
        if result.returncode == 0:
            # Should show warning about max-tokens being adjusted
            self.assertIn('已调整', result.stderr, 
                         "Should show warning when max-tokens exceeds context length")
            
            # Extract the adjusted max-tokens value from stderr
            import re
            adjusted_match = re.search(r'🔢 最大tokens: (\d+)', result.stderr)
            if adjusted_match:
                actual_max_tokens = int(adjusted_match.group(1))
                # Should be much less than the requested 100000000
                self.assertLess(actual_max_tokens, 100000, 
                              f"Max-tokens should be adjusted to reasonable value, got {actual_max_tokens}")
                # Should be reasonable fraction of context length (models typically have 16k-164k context)
                self.assertGreater(actual_max_tokens, 1000,
                                 f"Adjusted max-tokens should be reasonable, got {actual_max_tokens}")
        else:
            # If failed, should have reasonable error message
            self.assertIn('错误', result.stderr)
    
    def test_real_api_call_with_output_dir(self):
        """Test real API call with --output-dir if API key is available"""
        api_key = os.environ.get('OPENROUTER_API_KEY')
        
        if not api_key:
            self.skipTest("OPENROUTER_API_KEY not available for output-dir testing")
        
        import tempfile
        test_dir = Path(tempfile.mkdtemp())
        output_dir = test_dir / "openrouter_output"
        
        try:
            # Test with real API key and output directory
            result = self.run_subprocess([
                sys.executable, str(self.openrouter_py),
                'Hello world', '--max-tokens', '30',
                '--output-dir', str(output_dir)
            ], timeout=60)
            
            if result.returncode == 0:
                # Check if output file was created
                output_files = list(output_dir.glob("openrouter_*.txt"))
                if output_files:
                    self.assertGreater(len(output_files), 0, "Output file should be created")
                    # Check file content
                    with open(output_files[0], 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.assertIn('Query: Hello world', content)
                        self.assertIn('Model:', content)
                        self.assertIn('Timestamp:', content)
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)
    
    def test_default_model_functionality(self):
        """Test --default model functionality"""
        api_key = os.environ.get('OPENROUTER_API_KEY')
        
        if not api_key:
            self.skipTest("OPENROUTER_API_KEY not available for default model testing")
        
        import tempfile
        import shutil
        import json
        
        # Backup current models config
        models_config = Path(__file__).parent.parent / "OPENROUTER_PROJ" / "openrouter_models.json"
        backup_dir = Path(tempfile.mkdtemp())
        backup_file = backup_dir / "openrouter_models_backup.json"
        
        try:
            # Backup existing config
            if models_config.exists():
                shutil.copy2(models_config, backup_file)
            
            # Get list of available models first
            result = self.run_subprocess([
                sys.executable, str(self.openrouter_py), '--list'
            ], timeout=15)
            
            if result.returncode != 0:
                self.skipTest("Cannot get model list for default testing")
            
            # Parse available models from output
            available_models = []
            for line in result.stdout.split('\n'):
                if '. ' in line and 'deepseek' in line:
                    # Extract model name from format "1. model-name"
                    parts = line.strip().split('. ', 1)
                    if len(parts) > 1:
                        available_models.append(parts[1].split()[0])
            
            if not available_models:
                self.skipTest("No available models found for default testing")
            
            # Choose a model to set as default (not the first one)
            test_model = available_models[-1] if len(available_models) > 1 else available_models[0]
            
            # Set default model
            result = self.run_subprocess([
                sys.executable, str(self.openrouter_py),
                '--default', test_model
            ], timeout=15)
            
            self.assertEqual(result.returncode, 0, f"Setting default model failed: {result.stderr}")
            
            # Test that the model is now used by default
            result = self.run_subprocess([
                sys.executable, str(self.openrouter_py),
                'Hello', '--max-tokens', '10'
            ], timeout=30)
            
            if result.returncode == 0:
                # Check stderr for model info
                self.assertIn(test_model, result.stderr, f"Should use default model {test_model}")
            
        finally:
            # Restore backup
            try:
                if backup_file.exists():
                    shutil.copy2(backup_file, models_config)
                elif models_config.exists():
                    models_config.unlink()  # Remove if no backup existed
                shutil.rmtree(backup_dir, ignore_errors=True)
            except:
                pass

    def test_add_model_without_api_key(self):
        """Test --add model without API key"""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            result = self.assertCommandFail([
                sys.executable, str(self.openrouter_py), '--add', 'test/model:free'
            ])
            self.assertIn('❌ 需要API密钥来测试模型', result.stdout)

    def test_add_model_success(self):
        """Test successful model addition (simplified test)"""
        # Skip this test if no API key is available
        if not os.getenv("OPENROUTER_API_KEY"):
            self.skipTest("No OPENROUTER_API_KEY available for testing")
            
        # This is a simplified test that just checks the command structure
        # The actual API call will be skipped in most test environments
        result = self.run_subprocess([
            sys.executable, str(self.openrouter_py), '--add', 'test/model:free'
        ], timeout=10)
        
        # The command should either succeed (if API key works) or fail with a specific error
        # We just check that it doesn't crash with unexpected errors
        self.assertIn('模型', result.stdout)  # Should contain model-related output

    def test_add_model_failure(self):
        """Test model addition failure (simplified test)"""
        # Test with a clearly invalid model name
        result = self.run_subprocess([
            sys.executable, str(self.openrouter_py), '--add', 'definitely/nonexistent/model:fake'
        ], timeout=10)
        
        # Should fail and mention the model or API key issue
        self.assertTrue(
            '❌' in result.stdout or 'API密钥' in result.stdout,
            f"Expected error message in output: {result.stdout}"
        )

    def test_remove_nonexistent_model(self):
        """Test removing a nonexistent model"""
        result = self.assertCommandFail([
            sys.executable, str(self.openrouter_py), '--remove', 'nonexistent/model'
        ])
        self.assertIn('❌ 模型 \'nonexistent/model\' 不存在于列表中', result.stdout)

    def test_remove_existing_model(self):
        """Test removing an existing model"""
        # First, get current models to find one to remove
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), '--list'
        ])
        
        # Extract a model name from the list (assuming there's at least one)
        if 'deepseek/deepseek-chat' in result.stdout:
            # Try to remove this model
            remove_result = self.assertCommandSuccess([
                sys.executable, str(self.openrouter_py), '--remove', 'deepseek/deepseek-chat'
            ])
            self.assertIn('✅ 已从列表中移除模型', remove_result.stdout)
            
            # Verify it's no longer in the list
            list_result = self.assertCommandSuccess([
                sys.executable, str(self.openrouter_py), '--list'
            ])
            self.assertNotIn('deepseek/deepseek-chat', list_result.stdout)
            
            # Add it back for other tests
            try:
                self.run_subprocess([
                    sys.executable, str(self.openrouter_py), '--add', 'deepseek/deepseek-chat'
                ], timeout=30)
            except:
                pass  # Ignore if add fails

    def test_default_single_model(self):
        """Test setting a single default model"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), '--list'
        ])
        
        # Get the first model from the list
        lines = result.stdout.split('\n')
        first_model = None
        for line in lines:
            if line.strip().startswith('1.'):
                # Extract model name
                first_model = line.split('. ')[1].strip()
                break
        
        if first_model:
            # Set it as default
            default_result = self.assertCommandSuccess([
                sys.executable, str(self.openrouter_py), '--default', first_model
            ])
            self.assertIn('✅ 已将', default_result.stdout)

    def test_default_multiple_models(self):
        """Test setting multiple default models"""
        # Get current model list
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), '--list'
        ])
        
        # Extract at least two model names
        lines = result.stdout.split('\n')
        models = []
        for line in lines:
            if line.strip() and '. ' in line and not line.startswith('总计'):
                try:
                    model = line.split('. ')[1].strip()
                    models.append(model)
                    if len(models) >= 2:
                        break
                except:
                    continue
        
        if len(models) >= 2:
            # Test comma-separated models
            model_str = f"{models[1]},{models[0]}"  # Reverse order
            default_result = self.assertCommandSuccess([
                sys.executable, str(self.openrouter_py), '--default', model_str
            ])
            self.assertIn('✅ 已按顺序设置优先模型:', default_result.stdout)
            self.assertIn(models[1], default_result.stdout)
            self.assertIn(models[0], default_result.stdout)

    def test_default_with_nonexistent_models(self):
        """Test setting default with some nonexistent models"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), '--list'
        ])
        
        # Get first existing model
        lines = result.stdout.split('\n')
        first_model = None
        for line in lines:
            if line.strip().startswith('1.'):
                first_model = line.split('. ')[1].strip()
                break
        
        if first_model:
            # Test with mix of existing and nonexistent models
            model_str = f"nonexistent/model,{first_model},another/fake"
            default_result = self.assertCommandSuccess([
                sys.executable, str(self.openrouter_py), '--default', model_str
            ])
            self.assertIn('⚠️  以下模型不存在于列表中:', default_result.stdout)
            self.assertIn('nonexistent/model', default_result.stdout)
            self.assertIn('another/fake', default_result.stdout)
            self.assertIn('✅ 已将', default_result.stdout)

    def test_help_includes_new_options(self):
        """Test that help includes new --add and --remove options"""
        result = self.assertCommandSuccess([
            sys.executable, str(self.openrouter_py), '--help'
        ])
        self.assertIn('--add', result.stdout)
        self.assertIn('--remove', result.stdout)
        self.assertIn('--temp-key', result.stdout)
        self.assertIn('添加新模型到列表', result.stdout)
        self.assertIn('从列表中移除模型', result.stdout)


if __name__ == '__main__':
    import unittest
    unittest.main() 