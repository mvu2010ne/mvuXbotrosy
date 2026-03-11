import unicodedata
import re
import difflib
from zlapi.models import Message, ZaloAPIException, Mention, MultiMention, ThreadType
from config import ADMIN
from datetime import datetime
import time
import json

# Description of the combined script
des = {
    'tác giả': " Minh Vũ Shinn Cte",
    'mô tả': "🔍 Quản lý và tìm kiếm thành viên trong nhóm Zalo thông qua link nhóm.",
    'tính năng': [
        "🔗 Lấy ID nhóm từ liên kết Zalo mà không cần tham gia.",
        "📋 Lệnh group.linkfind: Tìm và liệt kê thông tin thành viên theo tên hoặc viết tắt từ link nhóm.",
        "🏷️ Lệnh group.linktag: Tag trực tiếp các thành viên khớp tên từ link nhóm (yêu cầu quyền admin).",
        "✅ Kiểm tra quyền admin tự động cho lệnh group.linktag.",
        "⏱️ Thêm độ trễ giữa các yêu cầu API để tránh lỗi.",
        "⚠️ Thông báo lỗi chi tiết nếu không tìm thấy thành viên, link không hợp lệ, hoặc gặp vấn đề API."
    ],
    'hướng dẫn sử dụng': [
        "📩 Gửi lệnh group.linkfind <link nhóm> <tên> để tìm thành viên trong nhóm từ link.",
        "📩 Gửi lệnh group.linktag <link nhóm> <tên> để tag thành viên khớp tên (chỉ admin).",
        "📌 Ví dụ: group.linkfind https://zalo.me/g/abc123 Tèo hoặc group.linktag https://zalo.me/g/abc123 Nam.",
        "✅ Nhận danh sách thành viên hoặc tag trực tiếp từ nhóm được chỉ định."
    ]
}

# Hard-coded admin ID (replace with actual admin check logic if needed)
def is_admin(author_id):
    return author_id in ADMIN
    
# Function to normalize text (remove diacritics and convert to lowercase)
def normalize_text(text):
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.lower().strip()

# Function to check if search terms match a name (exact or fuzzy)
def match_name(search_term, name, fuzzy_threshold=0.85):
    norm_search = normalize_text(search_term)
    norm_name = normalize_text(name)
    search_words = norm_search.split()

    # Exact match: all search words must be in the name
    if all(word in norm_name for word in search_words):
        return True, 1.0  # Exact match with perfect score

    # Fuzzy match: check similarity of full search term to name
    similarity = difflib.SequenceMatcher(None, norm_search, norm_name).ratio()
    if similarity >= fuzzy_threshold:
        return True, similarity

    return False, 0.0

# Function to find similar names for suggestions
def find_similar_names(search_term, members, max_suggestions=3, similarity_threshold=0.7):
    norm_search = normalize_text(search_term)
    suggestions = []
    for member in members:
        dName = member.get('zaloName', '')
        norm_name = normalize_text(dName)
        similarity = difflib.SequenceMatcher(None, norm_search, norm_name).ratio()
        if similarity >= similarity_threshold:
            suggestions.append((dName, similarity))
    # Sort by similarity (descending) and limit to max_suggestions
    suggestions.sort(key=lambda x: x[1], reverse=True)
    return suggestions[:max_suggestions]

# Function to extract group ID from a Zalo group link
def get_group_id_from_link(client, url):
    try:
        url = url.strip()
        group_info = client.getiGroup(url)
        if not isinstance(group_info, dict) or 'groupId' not in group_info:
            return None, f"Không lấy được thông tin nhóm từ: {url}"
        group_id = group_info['groupId']
        return group_id, None
    except ZaloAPIException as e:
        return None, f"Lỗi API: {str(e)}"
    except Exception as e:
        return None, f"Lỗi không xác định: {str(e)}"

# Function to get group members using group ID and memVerList
def get_group_members(client, thread_id):
    try:
        # Fetch group info using fetchGroupInfo
        group_info = client.fetchGroupInfo(thread_id).gridInfoMap.get(thread_id)
        if not group_info:
            return None, "Không thể lấy thông tin nhóm."
        
        # Get member IDs from memVerList
        member_ids = group_info.get('memVerList', [])
        if not member_ids:
            return None, "Nhóm không có thành viên hoặc danh sách trống."

        # Fetch detailed member info
        members = []
        for member_id in member_ids:
            # Remove "_0" suffix if present
            if isinstance(member_id, str) and member_id.endswith('_0'):
                member_id = member_id.rsplit('_', 1)[0]
            try:
                info = client.fetchUserInfo(member_id)
                info = info.unchanged_profiles or info.changed_profiles
                info = info.get(str(member_id))
                if info:
                    members.append({
                        'id': member_id,
                        'dName': info.zaloName,  # For compatibility with existing code
                        'zaloName': info.zaloName  # Full name for accurate search
                    })
                # Add delay to avoid API rate limits
                time.sleep(0.5)
            except Exception as e:
                print(f"[DEBUG] Failed to fetch info for member {member_id}: {str(e)}")
                continue  # Skip if info fetch fails
        print(f"[DEBUG] Retrieved {len(members)} members from group {thread_id}")
        return members, None
    except ZaloAPIException as e:
        return None, f"Lỗi API: {str(e)}"
    except Exception as e:
        return None, f"Lỗi không xác định: {str(e)}"

# Function to check if the user is an admin
def is_admin(author_id):
    return str(author_id) == ADMIN_ID

# Function to handle group.linkfind command
def handle_linkfind(message, message_object, thread_id, thread_type, author_id, client):
    # Split command and validate input
    parts = message.strip().split(" ", 2)
    if len(parts) < 3 or not parts[1].strip() or not parts[2].strip():
        client.replyMessage(
            Message(text="Nhập link nhóm và tên thành viên cần tìm.\nVí dụ: group.linkfind https://zalo.me/g/abc123 Tèo"),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    link = parts[1].strip()
    search_term = parts[2].strip()

    # Extract group ID from link
    group_id, error = get_group_id_from_link(client, link)
    if error:
        client.replyMessage(Message(text=error), message_object, thread_id, thread_type, ttl=60000)
        return

    # Add delay to avoid API rate limits
    time.sleep(1)

    # Get group members
    members, error = get_group_members(client, group_id)
    if error:
        client.replyMessage(Message(text=error), message_object, thread_id, thread_type, ttl=60000)
        return

    # Find members matching the search term
    found_members = []
    for member in members:
        zaloName = member.get('zaloName', '')
        is_match, similarity = match_name(search_term, zaloName)
        if is_match:
            found_members.append({'dName': zaloName, 'id': member['id'], 'similarity': similarity})
        print(f"[DEBUG] Checking name: {zaloName}, Normalized: {normalize_text(zaloName)}")

    if found_members:
        # Sort by similarity (descending) to prioritize exact matches
        found_members.sort(key=lambda x: x['similarity'], reverse=True)
        # Format response
        response_text = f"🔎 Danh sách thành viên '{search_term}' tìm thấy trong nhóm:\n\n"
        for i, member in enumerate(found_members[:100], 1):  # Limit to 100 members
            response_text += f"{i}.\n- Tên: {member['dName']}, ID: {member['id']}\n\n"
        client.replyMessage(Message(text=response_text), message_object, thread_id, thread_type, ttl=86400000)
        return

    # If no matches, suggest similar names
    suggestions = find_similar_names(search_term, members)
    if suggestions:
        suggestion_text = f"Không tìm thấy thành viên nào có tên chứa '{search_term}'. Bạn có ý chỉ một trong những người này không?\n\n"
        for i, (name, similarity) in enumerate(suggestions, 1):
            suggestion_text += f"{i}. {name} (giống {int(similarity * 100)}%)\n"
        suggestion_text += "\nVui lòng kiểm tra lại tên hoặc link nhóm."
    else:
        suggestion_text = f"Không tìm thấy thành viên nào có tên chứa '{search_term}' trong nhóm. Vui lòng kiểm tra lại tên hoặc link nhóm."

    client.replyMessage(
        Message(text=suggestion_text),
        message_object, thread_id, thread_type, ttl=86400000
    )

# Function to handle group.linktag command
def handle_linktag(message, message_object, thread_id, thread_type, author_id, client):
    # Check if the user is an admin
    if not is_admin(author_id):
        client.replyMessage(
            Message(text="Chỉ admin mới có thể sử dụng lệnh này."),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    # Split command and validate input
    parts = message.strip().split(" ", 2)
    if len(parts) < 3 or not parts[1].strip() or not parts[2].strip():
        client.replyMessage(
            Message(text="Nhập link nhóm và tên thành viên cần tag.\nVí dụ: group.linktag https://zalo.me/g/abc123 Nam"),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    link = parts[1].strip()
    search_term = parts[2].strip()

    # Extract group ID from link
    group_id, error = get_group_id_from_link(client, link)
    if error:
        client.replyMessage(Message(text=error), message_object, thread_id, thread_type, ttl=60000)
        return

    # Add delay to avoid API rate limits
    time.sleep(1)

    # Get group members
    members, error = get_group_members(client, group_id)
    if error:
        client.replyMessage(Message(text=error), message_object, thread_id, thread_type, ttl=60000)
        return

    # Find members matching the search term
    found_members = []
    for member in members:
        zaloName = member.get('zaloName', '')
        is_match, similarity = match_name(search_term, zaloName)
        if is_match:
            found_members.append({'dName': zaloName, 'id': member['id'], 'similarity': similarity})
        print(f"[DEBUG] Checking name: {zaloName}, Normalized: {normalize_text(zaloName)}")

    if not found_members:
        # If no matches, suggest similar names
        suggestions = find_similar_names(search_term, members)
        if suggestions:
            suggestion_text = f"Không tìm thấy thành viên nào có tên chứa '{search_term}'. Bạn có ý chỉ một trong những người này không?\n\n"
            for i, (name, similarity) in enumerate(suggestions, 1):
                suggestion_text += f"{i}. {name} (giống {int(similarity * 100)}%)\n"
            suggestion_text += "\nVui lòng kiểm tra lại tên hoặc link nhóm."
        else:
            suggestion_text = f"Không tìm thấy thành viên nào có tên chứa '{search_term}' trong nhóm. Vui lòng kiểm tra lại tên hoặc link nhóm."

        client.replyMessage(
            Message(text=suggestion_text),
            message_object, thread_id, thread_type, ttl=60000
        )
        return

    # Create tagged message
    found_members.sort(key=lambda x: x['similarity'], reverse=True)  # Sort by similarity
    text = ""
    mentions = []
    offset = 0
    for member in found_members:
        user_id = str(member['id'])
        user_name = member['dName']
        text += f"{user_name} "
        mentions.append(Mention(uid=user_id, offset=offset, length=len(user_name), auto_format=False))
        offset += len(user_name) + 1
    client.replyMessage(
        Message(text=text.strip(), mention=MultiMention(mentions)),
        message_object, thread_id, thread_type, ttl=60000
    )

# Function to return commands
def get_mitaizl():
    return {
        'group.linkfind': handle_linkfind,
        'group.linktag': handle_linktag
    }