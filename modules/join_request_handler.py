from zlapi import ZaloAPI, ZaloAPIException, GroupEventType
from zlapi.models import *
import logging
import json

def load_excluded_groups(filepath="excluded_event.json"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [entry["group_id"] for entry in data if "group_id" in entry]
    except Exception as e:
        logging.error(f"Lỗi khi đọc excluded_event.json: {e}")
        return []

des = {
    'version': "1.0.0",
    'credits': "Minh Vũ Shinn Cte FIX",
    'description': "Auto-approve join requests for Zalo groups"
}

EXCLUDED_GROUPS = load_excluded_groups()

logging.basicConfig(
    level=logging.ERROR,
    filename="bot_error.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class JoinRequestHandler(ZaloAPI):
    def handleGroupPending(self, members, groupId, isApprove=True):
        """Approve/Deny pending users to the group from the group's approval.
        
        Client must be the Owner of the group.
        
        Args:
            members (str | list): One or More member IDs to handle
            groupId (int | str): ID of the group to handle pending members
            isApprove (bool): Approve/Reject pending members (True | False)
            
        Returns:
            object: `Group` handle pending responses
            dict: A dictionary/object containing error responses
        
        Raises:
            ZaloAPIException: If request failed
        """
        if isinstance(members, list):
            members = [str(member) for member in members]
        else:
            members = [str(members)]
        
        params = {
            "params": self._encode({
                "grid": str(groupId),
                "members": members,
                "isApprove": 1 if isApprove else 0
            }),
            "zpw_ver": 645,
            "zpw_type": 30
        }
        
        response = self._get("https://tt-group-wpa.chat.zalo.me/api/group/pending-mems/review", params=params)
        data = response.json()
        results = data.get("data") if data.get("error_code") == 0 else None
        if results:
            results = self._decode(results)
            results = results.get("data") if results.get("data") else results
            if results == None:
                results = {"error_code": 1337, "error_message": "Data is None"}
            
            if isinstance(results, str):
                try:
                    results = json.loads(results)
                except:
                    results = {"error_code": 1337, "error_message": results}
                
            return Group.fromDict(results, None)
            
        error_code = data.get("error_code")
        error_message = data.get("error_message") or data.get("data")
        raise ZaloAPIException(f"Error #{error_code} when sending requests: {error_message}")

    def handle_join_request(self, event_data, event_type):
        if event_type != GroupEventType.JOINREQUEST:
            return

        thread_id = event_data['groupId']
        if thread_id in EXCLUDED_GROUPS:
            logging.info(f"Nhóm {thread_id} nằm trong danh sách loại trừ, không xử lý yêu cầu tham gia.")
            return

        try:
            members = [member['id'] for member in event_data.get('updateMembers', [])]
            if not members:
                logging.info(f"Không có thành viên trong yêu cầu tham gia nhóm {thread_id}.")
                return

            # Approve all pending members
            result = self.handleGroupPending(members, thread_id, isApprove=True)
            logging.info(f"Duyệt thành công {len(members)} thành viên vào nhóm {thread_id}.")
            
            # Send confirmation message
            message_text = f"Đã duyệt {len(members)} thành viên vào nhóm!"
            message = Message(text=message_text)
            self.sendMessage(message, thread_id, ThreadType.GROUP)
            
        except ZaloAPIException as e:
            logging.error(f"Lỗi khi duyệt thành viên vào nhóm {thread_id}: {e}")
        except Exception as e:
            logging.error(f"Lỗi không xác định khi xử lý yêu cầu tham gia nhóm {thread_id}: {e}")

def get_mitaizl():
    return {
        'join_request': None
    }