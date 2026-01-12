"""Credential management using system keyring"""
import keyring


class CredentialManager:
    """Manages credential storage and retrieval using system keyring"""
    
    SERVICE_NAME = "CoursePortalLMS"
    
    def __init__(self):
        self.service_name = self.SERVICE_NAME
    
    def save_credentials(self, username, password):
        """Save credentials to system keyring"""
        try:
            keyring.set_password(self.service_name, username, password)
            # Store that we have saved credentials
            keyring.set_password(self.service_name, "_remember_me", "true")
            keyring.set_password(self.service_name, "_username", username)
        except Exception as e:
            print(f"Error saving credentials: {e}")
    
    def load_saved_credentials(self):
        """Load saved credentials from system keyring"""
        try:
            # Check if we have saved credentials
            remember_me = keyring.get_password(self.service_name, "_remember_me")
            if remember_me == "true":
                username = keyring.get_password(self.service_name, "_username")
                if username:
                    password = keyring.get_password(self.service_name, username)
                    if password:
                        return {
                            "username": username,
                            "password": password,
                            "remember_me": True
                        }
        except Exception as e:
            print(f"Error loading credentials: {e}")
        return None
    
    def clear_saved_credentials(self):
        """Clear saved credentials from system keyring"""
        try:
            username = keyring.get_password(self.service_name, "_username")
            if username:
                keyring.delete_password(self.service_name, username)
            keyring.delete_password(self.service_name, "_remember_me")
            keyring.delete_password(self.service_name, "_username")
        except Exception as e:
            print(f"Error clearing credentials: {e}")
