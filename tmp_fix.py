lines = open('backend/app/services/ai_service.py').readlines()
lines[151] = '                return base_system_prompt\n'
lines.insert(152, '\n')
lines.insert(153, '            return base_system_prompt + memory_context\n')
lines.insert(154, '        except Exception as e:\n')
lines.insert(155, '            logger.error(f\"Error injecting memory context: {e}\")\n')
lines.insert(156, '            return base_system_prompt\n')
open('backend/app/services/ai_service.py', 'w').writelines(lines)
print('Done')