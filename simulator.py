import json
import time
import hmac
import hashlib

SHARED_SECRET_KEY = b"ORBIT_SHIELD_SECRET_KEY_2026"
ALLOWED_COMMANDS = ["THRUSTER_FIRE", "REBOOT_COMPUTER", "CAMERA_ON", "SAFE_MODE"]
MAX_THRUSTER_DURATION = 60  
REPLAY_WINDOW_SECONDS = 300 

def calculate_hmac(message_dict):
    msg_copy = message_dict.copy()
    msg_copy.pop("hmac_signature", None) 
    serialized_data = json.dumps(msg_copy, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hmac.new(SHARED_SECRET_KEY, serialized_data, hashlib.sha256).hexdigest()

def validate_satellite_command(command):
    required_fields = ["command_id", "command_type", "timestamp", "sequence_number", "payload", "hmac_signature"]
    for field in required_fields:
        if field not in command:
            return False, f"REJECTED: MISSING REQUIRED STRUCTURAL FIELD: {field}"

    cmd_type = command["command_type"]
    if cmd_type not in ALLOWED_COMMANDS:
        return False, f"REJECTED: UNAUTHORIZED COMMAND TYPE: '{cmd_type}'"

    current_time = int(time.time())
    if abs(current_time - command["timestamp"]) > REPLAY_WINDOW_SECONDS:
        return False, f"REJECTED: STALE TIMESTAMP (REPLAY ATTACK THREAT DETECTED)"

    if cmd_type == "THRUSTER_FIRE":
        duration = command["payload"].get("duration_seconds", 0)
        if not (0 < duration <= MAX_THRUSTER_DURATION):
            return False, f"REJECTED: PARAMETER OUT OF BOUNDS (DURATION {duration}s EXCEEDS MAX {MAX_THRUSTER_DURATION}s)"

    computed_sig = calculate_hmac(command)
    if not hmac.compare_digest(command["hmac_signature"], computed_sig):
        return False, "REJECTED: CRYPTOGRAPHIC SIGNATURE MISMATCH (MAN-IN-THE-MIDDLE TAMPERING)"

    return True, "ACCEPTED: COMMAND VALIDATED SUCCESSFULLY - ROUTED TO SPACECRAFT PAYLOAD CORE"

if __name__ == "__main__":
    print("--- STARTING ORBIT SHIELD COMMAND SIMULATION AUDIT --- \n")
    
    valid_test_command = {
        "command_id": "CMD-2026-0042",
        "command_type": "THRUSTER_FIRE",
        "timestamp": int(time.time()),
        "sequence_number": 105,
        "payload": {"duration_seconds": 12, "direction": "NORTH"}
    }
    valid_test_command["hmac_signature"] = calculate_hmac(valid_test_command)

    test_cases = {
        "VALID PACKET TRAFFIC": valid_test_command,
        "MALICIOUS ALTERATION (TAMPERED SIGNATURE)": {**valid_test_command, "hmac_signature": "invalid_signature_hash_xyz"},
        "UNAUTHORIZED ATTACK COMMAND": {**valid_test_command, "command_type": "SELF_DESTRUCT", "hmac_signature": ""},
        "OUT-OF-BOUNDS INSTRUCTION": {**valid_test_command, "payload": {"duration_seconds": 999, "direction": "NORTH"}, "hmac_signature": ""},
        "STALE TIMEFRAME (REPLAY EXPLOIT)": {**valid_test_command, "timestamp": 1600000000, "hmac_signature": ""}
    }

    for label, payload in test_cases.items():
        if label in ["UNAUTHORIZED ATTACK COMMAND", "OUT-OF-BOUNDS INSTRUCTION"]:
            payload["hmac_signature"] = calculate_hmac(payload)
            
        success, log_msg = validate_satellite_command(payload)
        status_icon = "🟢" if success else "🔴"
        print(f"[{label}]\nResult: {status_icon} {log_msg}\n{'-'*60}")
