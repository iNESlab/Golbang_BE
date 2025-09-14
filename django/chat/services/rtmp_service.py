# 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
"""
RTMP 스트리밍 서비스
nginx-rtmp 미디어 서버와 연동하여 오디오 스트림을 관리합니다.
"""
"""
import asyncio
import subprocess
import logging
import os
import tempfile
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class RTMPStreamService:
    def __init__(self):
        self.active_streams: Dict[str, subprocess.Popen] = {}
        self.rtmp_lock = asyncio.Lock()
        self.named_pipes: Dict[str, str] = {}  # stream_key -> pipe_path
        
        # RTMP 서버 설정
        self.rtmp_server = "rtmp://nginx-rtmp:1935/live"
        
    async def start_background_stream(self, stream_key: str, audio_file: str) -> bool:
        """배경음악 스트림 시작"""
        try:
            async with self.rtmp_lock:
                # 기존 스트림 정리
                await self._stop_stream(stream_key)
                
                # FFmpeg 명령어 구성
                rtmp_url = f"{self.rtmp_server}/{stream_key}"
                
                # Safari 호환성을 위한 더미 비디오 트랙 추가
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-re',                                    # 실시간 속도
                    '-stream_loop', '-1',                     # 무한 반복
                    '-i', audio_file,                         # 오디오 입력
                    '-f', 'lavfi',                           # 더미 비디오 생성
                    '-i', 'color=black:size=1280x720:rate=1', # 1fps 검은 화면
                    '-c:a', 'aac',                           # 오디오 코덱
                    '-b:a', '128k',                          # 오디오 비트레이트
                    '-c:v', 'libx264',                       # 비디오 코덱
                    '-preset', 'ultrafast',                  # 빠른 인코딩
                    '-tune', 'zerolatency',                  # 낮은 지연시간
                    '-pix_fmt', 'yuv420p',                   # 호환성
                    '-g', '2',                               # GOP 크기 (2초)
                    '-keyint_min', '2',                      # 최소 키프레임 간격
                    '-r', '1',                               # 비디오 프레임레이트 1fps
                    '-f', 'flv',                             # RTMP 출력 형식
                    rtmp_url
                ]
                
                logger.info(f"🎵 Starting background stream: {stream_key}")
                logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
                
                # 프로세스 시작 (비동기적으로 변경)
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE
                )
                
                self.active_streams[stream_key] = process
                
                # 프로세스 모니터링 시작
                asyncio.create_task(self._monitor_stream(stream_key, process))
                
                logger.info(f"✅ Background stream started successfully: {stream_key}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to start background stream {stream_key}: {e}")
            return False
    
    async def insert_commentary(self, stream_key: str, audio_data: bytes, duration_seconds: float = 5.0) -> bool:
        """해설 오디오를 배경음악과 믹싱하여 스트림에 삽입"""
        try:
            async with self.rtmp_lock:
                logger.info(f"🎤 Starting mixed commentary stream: {stream_key} ({duration_seconds}s)")
                
                # 1. 기존 스트림 중지
                await self._stop_stream(stream_key)
                await asyncio.sleep(2)  # 정리 시간
                
                # 2. 임시 파일에 해설 오디오 저장
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    temp_file.write(audio_data)
                    commentary_path = temp_file.name
                
                try:
                    # 3. 배경음악과 해설을 믹싱한 스트림 생성 (다른 스트림 키 사용)
                    background_audio = '/app/media/audio/background_default.mp3'
                    commentary_stream_key = f"{stream_key}_commentary"
                    rtmp_url = f"{self.rtmp_server}/{commentary_stream_key}"
                    
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-re', '-stream_loop', '-1', '-i', background_audio,  # 배경음악 (무한반복)
                        '-i', commentary_path,                                # 해설 오디오
                        '-f', 'lavfi', '-i', 'color=black:size=1280x720:rate=1',  # 더미 비디오
                        '-filter_complex', 
                        f'[0:a]volume=0.0[bg];[1:a]volume=2.0[comm];[bg][comm]amix=inputs=2:duration=first:dropout_transition=0[mixed]',
                        '-map', '[mixed]',     # 믹싱된 오디오
                        '-map', '2:v',         # 더미 비디오
                        '-c:a', 'aac', '-b:a', '128k',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency',
                        '-pix_fmt', 'yuv420p', '-g', '2', '-keyint_min', '2', '-r', '1',
                        '-t', str(duration_seconds),  # 해설 길이만큼만
                        '-f', 'flv',
                        rtmp_url
                    ]
                    
                    logger.info(f"🎵 Mixed stream command: {' '.join(ffmpeg_cmd[:10])}...")
                    
                    # 믹싱된 스트림 실행 (비동기로 변경)
                    process = await asyncio.create_subprocess_exec(
                        *ffmpeg_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    try:
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(), 
                            timeout=duration_seconds + 10
                        )
                        
                        if process.returncode == 0:
                            logger.info(f"✅ Mixed commentary stream completed: {commentary_stream_key}")
                            
                            # 4. 해설 완료 후 배경음악만 다시 시작
                            await self._restart_background_stream(stream_key)
                            logger.info(f"📡 배경음악 재시작 완료: {stream_key}")
                            return True
                        else:
                            logger.error(f"❌ Mixed commentary stream failed: {stderr.decode() if stderr else 'Unknown error'}")
                            # 실패 시에도 배경음악 재시작 시도
                            await self._restart_background_stream(stream_key)
                            logger.info(f"📡 실패 시 배경음악 재시작: {stream_key}")
                            return False
                            
                    except asyncio.TimeoutError:
                        logger.error(f"⏰ Mixed commentary stream timeout: {commentary_stream_key}")
                        process.kill()
                        await process.wait()
                        # 타임아웃 시에도 배경음악 재시작
                        await self._restart_background_stream(stream_key)
                        logger.info(f"📡 타임아웃 시 배경음악 재시작: {stream_key}")
                        return False
                        
                finally:
                    # 임시 파일 정리
                    try:
                        os.unlink(commentary_path)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"❌ Failed to insert commentary {stream_key}: {e}")
            # 에러 시에도 배경음악 재시작 시도 (임시 비활성화)
            # try:
            #     await self._restart_background_stream(stream_key)
            # except:
            #     pass
            logger.info(f"📡 (임시 비활성화) 예외 시 배경음악 재시작: {stream_key}")
            return False
    
    async def _stop_stream(self, stream_key: str) -> None:
        """스트림 중지"""
        if stream_key in self.active_streams:
            process = self.active_streams[stream_key]
            try:
                if process.returncode is None:  # 프로세스가 아직 실행 중
                    # SIGTERM으로 정상 종료 시도
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        # 강제 종료
                        process.kill()
                        await process.wait()
                    
                    logger.info(f"🛑 Stream stopped: {stream_key}")
                    
            except ProcessLookupError:
                pass  # 이미 종료된 프로세스
            except Exception as e:
                logger.error(f"❌ Error stopping stream {stream_key}: {e}")
            
            del self.active_streams[stream_key]
    
    async def _monitor_stream(self, stream_key: str, process) -> None:
        """스트림 프로세스 모니터링 (asyncio 프로세스용)"""
        try:
            # 프로세스 완료 대기 (비동기)
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                stderr_output = stderr.decode('utf-8') if stderr else "No error output"
                logger.error(f"❌ Stream process failed {stream_key} (code {process.returncode}): {stderr_output}")
            else:
                logger.info(f"✅ Stream process completed normally: {stream_key}")
                
        except Exception as e:
            logger.error(f"❌ Error monitoring stream {stream_key}: {e}")
        finally:
            # 정리
            if stream_key in self.active_streams:
                del self.active_streams[stream_key]
    
    async def stop_all_streams(self) -> None:
        """모든 스트림 중지"""
        stream_keys = list(self.active_streams.keys())
        for stream_key in stream_keys:
            await self._stop_stream(stream_key)
        logger.info("🛑 All streams stopped")
    
    async def get_stream_status(self, stream_key: str) -> Dict:
        """스트림 상태 조회"""
        is_active = stream_key in self.active_streams
        process = self.active_streams.get(stream_key)
        
        status = {
            'active': is_active,
            'pid': process.pid if process else None,
            'running': process.returncode is None if process else False
        }
        
        return status
    
    async def _restart_background_stream(self, stream_key: str) -> bool:
        """배경음악 스트림 재시작"""
        try:
            logger.info(f"🎵 Restarting background stream: {stream_key}")
            
            # 기존 스트림 완전히 정리 (혹시 남아있을 수 있는 프로세스)
            await self._stop_stream(stream_key)
            await asyncio.sleep(3)  # nginx-rtmp 정리 시간
            logger.info(f"🧹 Cleaned up existing stream: {stream_key}")
            
            # 배경음악 파일 경로
            audio_file = '/app/media/audio/background_default.mp3'
            
            # 배경음악 스트림 재시작
            success = await self.start_background_stream(stream_key, audio_file)
            
            if success:
                logger.info(f"✅ Background stream restarted successfully: {stream_key}")
            else:
                logger.error(f"❌ Failed to restart background stream: {stream_key}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Error restarting background stream {stream_key}: {e}")
            return False
    
    def get_hls_url(self, stream_key: str) -> str:
        """HLS 플레이리스트 URL 반환"""
        return f"http://localhost/hls/{stream_key}/index.m3u8"

# 싱글톤 인스턴스
rtmp_service = RTMPStreamService()
"""