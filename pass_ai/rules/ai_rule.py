# rules/ai_rule.py
from rules.base_rule import BaseRule

class AIGeneratorRule(BaseRule):
    def __init__(self, model_path="models/pass_transformer_v1", num_return_sequences=10):
        self.model_path = model_path
        self.num_return_sequences = num_return_sequences

    def _format_input(self, profile):
        prompt = f"<NAME> {profile.get('fullname', '')} "
        prompt += f"<DOB> {profile.get('birthdate', '')} "
        prompt += f"<REL> {profile.get('relative_name', '')} "
        return prompt.strip()

    # ĐỔI TÊN HÀM Ở ĐÂY: apply -> execute
    def execute(self, passwords, profile):
        input_text = self._format_input(profile)
        
        # Mock dữ liệu sinh ra từ AI:
        ai_passwords = [
            f"{profile.get('fullname', '').split()[-1].capitalize()}123" if profile.get('fullname') else "Base123",
            f"{profile.get('fullname', '').split()[-1].capitalize()}@{profile.get('birthdate', '')[-4:]}" if profile.get('fullname') and profile.get('birthdate') else "Base@2026",
            "Nguyen1998@",
            "VanA_98"
        ]

        passwords.update(ai_passwords)
        return set(passwords)