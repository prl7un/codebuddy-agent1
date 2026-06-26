import json
import os
import urllib.request
import urllib.parse

def lambda_handler(event, context):
    print("Received Bedrock event:", json.dumps(event))
    
    # 1. Bedrock Agent가 넘겨준 정보 추출
    # 에이전트 빌더 기능(Function) 구조에 맞게 안전하게 추출
    function_name = event.get('function')
    parameters = event.get('parameters', [])
    
    def get_param(name):
        for p in parameters:
            if p['name'] == name:
                return p['value']
        return None

    # 2. 깃허브 토큰 안전하게 꺼내기
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        return build_response(event, "에러: 람다 환경변수에 GITHUB_TOKEN이 없습니다.")

    # 3. 댓글 달기 기능 수행 (에이전트 빌더의 함수명 'post_pr_1'과 완벽 매칭)
    if function_name == 'post_pr_1':
        owner = get_param('owner')
        repo = get_param('repo')
        pr_number = get_param('pr_number')
        comment = get_param('comment')
        
        # [보안 강화] 입력값이 올바른지 검증 (숫자인지, 빈 값은 없는지)
        if not owner or not repo or not str(pr_number).isdigit():
            return build_response(event, "에러: 유효하지 않은 PR 정보입니다.")
            
        print(f"댓글 달기 시도 중: {owner}/{repo} PR #{pr_number}")
        
        # 경로 조작(Path Traversal) 방지를 위한 URL 안전 처리
        safe_owner = urllib.parse.quote(str(owner).replace('/', ''))
        safe_repo = urllib.parse.quote(str(repo).replace('/', ''))
        safe_pr_number = urllib.parse.quote(str(pr_number))
        
        url = f"https://api.github.com/repos/{safe_owner}/{safe_repo}/issues/{safe_pr_number}/comments"
        
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        data = json.dumps({"body": comment}).encode('utf-8')
        
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req) as response:
                return build_response(event, "성공: GitHub PR에 댓글이 등록되었습니다.")
        except Exception as e:
            # 에러 발생 시 내부 시스템 정보 노출 최소화 (보안 가이드 준수)
            print(f"실제 내부 에러 원인 로그: {str(e)}")
            return build_response(event, "에러: GitHub API 호출 실패 (권한이나 주소를 확인하세요)")
            
    return build_response(event, f"에러: 알 수 없는 도구 호출 ({function_name})")

# Bedrock Agent 규격에 맞게 응답 포장
def build_response(event, response_text):
    print("Agent에게 돌려주는 대답:", response_text)
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get('actionGroup'),
            "function": event.get('function'),
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": response_text
                    }
                }
            }
        }
    }
