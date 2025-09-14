# 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
"""
import os
import asyncio
import logging
from datetime import datetime

from django.conf import settings

logger = logging.getLogger(__name__)

class HLSService:
    """단순화된 HLS 스트림 헬퍼 (오디오 전용).
    EventBroadcastService 가 배경 음악 스트림을 켜고 TTS 멘트를 세그먼트로 삽입할 때 사용한다.
    """

    def __init__(self):
        self.base_dir = os.path.join(settings.BASE_DIR, "static", "hls", "radio")
        os.makedirs(self.base_dir, exist_ok=True)
        self.ffmpeg_lock = asyncio.Lock()
        # club_id -> ffmpeg process
        self.processes = {}
        self.audio_files = {}
        self.stream_start_times = {}
        self.segment_counters = {}  # club_id별 세그먼트 카운터

    # ---------------------------------------------------------------------
    # 배경음악 스트림 ------------------------------------------------------
    # ---------------------------------------------------------------------
    async def start_stream(self, club_id: int, audio_file_path: str) -> str | None:
        """배경음악을 반복 재생하며 HLS 스트림을 시작한다."""
        if club_id in self.processes:
            logger.warning("club %s stream already running", club_id)
            return self._playlist_url(club_id)

        self.audio_files[club_id] = audio_file_path
        stream_dir = self._stream_dir(club_id)
        os.makedirs(stream_dir, exist_ok=True)

        # 스트림 시작 시간 기록 (음악 재개 위치 계산용)
        import time
        self.stream_start_times[club_id] = time.time()
        
        # 세그먼트 카운터 초기화 (처음 시작 시에만)
        if club_id not in self.segment_counters:
            self.segment_counters[club_id] = 0

        # 무한 반복을 보장하기 위해 filter_complex 사용
        command = [
            "ffmpeg",
            "-re",
            "-i", audio_file_path,
            "-filter_complex", "[0:a]aloop=loop=-1:size=2e+09[looped]",  # 무한 반복 필터
            "-map", "[looped]",
            "-c:a", "aac", "-b:a", "128k",
            "-f", "hls",
            "-hls_time", "4",
            "-hls_list_size", "10",  # 지연 시간 단축을 위해 줄임
            "-hls_flags", "delete_segments+append_list+program_date_time+split_by_time",
            "-start_number", str(self.segment_counters[club_id]),
            "-hls_segment_filename", os.path.join(stream_dir, "segment_%03d.ts"),
            os.path.join(stream_dir, "playlist.m3u8"),
        ]

        async with self.ffmpeg_lock:
            proc = await asyncio.create_subprocess_exec(*command,
                                                        stdout=asyncio.subprocess.PIPE,
                                                        stderr=asyncio.subprocess.PIPE)
            self.processes[club_id] = proc
            logger.info("✅ Stream started successfully for club %s", club_id)
            
            # 프로세스 상태 확인 (비동기로)
            asyncio.create_task(self._monitor_process(club_id, proc, "background_music"))

            return self._playlist_url(club_id)
        return None

    async def stop_stream(self, club_id: int):
        """FFmpeg 스트림을 안전하게 중단한다."""
        proc = self.processes.pop(club_id, None)
        self.audio_files.pop(club_id, None)
        self.stream_start_times.pop(club_id, None)

        if proc:
            logger.info("stopping stream for club %s", club_id)
            try:
                # 1. 정상적인 종료 시도
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                    logger.info("✅ club %s stream 정상 종료", club_id)
                except asyncio.TimeoutError:
                    # 2. 강제 종료
                    logger.warning("⏰ club %s stream 종료 타임아웃, 강제 종료", club_id)
                    proc.kill()
                    await proc.wait()
                    logger.info("🔥 club %s stream 강제 종료", club_id)
            except Exception as e:
                logger.error("FFmpeg 종료 오류 (club %s): %s", club_id, e)
        else:
            logger.debug("club %s: 종료할 프로세스 없음", club_id)
            
        # 3. 세그먼트 파일 정리 (선택적)
        await self._cleanup_segments(club_id)

    # ---------------------------------------------------------------------
    # Commentary -----------------------------------------------------------
    # ---------------------------------------------------------------------
    async def add_commentary_segment(self, club_id: int, audio_bytes: bytes):
        """해설 오디오를 FFmpeg로 실시간 스트리밍하여 라이브 상태 유지"""
        import tempfile, time
        stream_dir = self._stream_dir(club_id)
        os.makedirs(stream_dir, exist_ok=True)

        async with self.ffmpeg_lock:
            # 1. 배경음악 FFmpeg 프로세스 일시 중지
            logger.info("⏸️  Pausing background stream for commentary (club %s)", club_id)
            proc = self.processes.pop(club_id, None)
            if proc:
                try:
                    if proc.returncode is None:  # 프로세스가 아직 실행 중인지 확인
                        proc.terminate()
                        await asyncio.wait_for(proc.wait(), timeout=5.0)
                    else:
                        logger.info("ℹ️ Process already terminated (club %s)", club_id)
                except ProcessLookupError:
                    logger.info("ℹ️ Process already gone (club %s)", club_id)
                except asyncio.TimeoutError:
                    logger.warning("⚠️  FFmpeg (pause) did not terminate gracefully, killing.")
                    try:
                        if proc.returncode is None:  # 여전히 실행 중이면
                            proc.kill()
                            await proc.wait()
                    except ProcessLookupError:
                        logger.info("ℹ️ Process disappeared during kill (club %s)", club_id)
                except Exception as e:
                    logger.error("❌ Error terminating process (club %s): %s", club_id, e)

            # 2. 플레이리스트에 DISCONTINUITY 태그 추가
            main_playlist = os.path.join(stream_dir, "playlist.m3u8")
            try:
                with open(main_playlist, "a") as f:
                    f.write("\n#EXT-X-DISCONTINUITY\n")
                logger.info("🎬 Added DISCONTINUITY tag for commentary start.")
            except Exception as e:
                logger.error(f"❌ Failed to write DISCONTINUITY tag: {e}")

            # 3. 해설 오디오를 임시 파일로 저장
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            try:
                # 3. 현재 세그먼트 번호 가져오기
                current_segment_num = self._get_current_segment_number(club_id)
                if current_segment_num is not None:
                    self.segment_counters[club_id] = current_segment_num + 1
                else:
                    # 플레이리스트가 없으면 0부터 시작
                    self.segment_counters[club_id] = 0
                
                logger.info("🎤 Starting commentary stream from segment %d (club %s)", self.segment_counters[club_id], club_id)
                
                # 4. 해설 오디오를 FFmpeg로 실시간 스트리밍
                main_playlist = os.path.join(stream_dir, "playlist.m3u8")
                commentary_command = [
                    "ffmpeg",
                    "-re",  # 실시간 속도로 읽기
                    "-i", tmp_path,
                    "-c:a", "aac", "-b:a", "128k",
                    "-f", "hls",
                    "-hls_time", "4",
                    "-hls_list_size", "20",  # 해설 및 이전 세그먼트를 충분히 담을 수 있도록 일시적으로 늘림
                    "-hls_flags", "append_list+program_date_time+split_by_time",  # delete_segments 제거
                    "-start_number", str(self.segment_counters[club_id]),
                    "-hls_segment_filename", os.path.join(stream_dir, "segment_%03d.ts"),
                    main_playlist,
                ]
                
                logger.info("🔧 Starting commentary FFmpeg process with command: %s", ' '.join(commentary_command))
                commentary_proc = await asyncio.create_subprocess_exec(*commentary_command,
                                                                      stdout=asyncio.subprocess.PIPE,
                                                                      stderr=asyncio.subprocess.PIPE)
                
                # 해설 프로세스 완료까지 대기
                stdout, stderr = await commentary_proc.communicate()
                
                if commentary_proc.returncode == 0:
                    logger.info("✅ Commentary stream completed successfully (club %s)", club_id)
                else:
                    logger.error("❌ Commentary stream failed (club %s) with return code %d", club_id, commentary_proc.returncode)
                    if stderr:
                        logger.error("❌ Commentary FFmpeg stderr: %s", stderr.decode())
                
            finally:
                # 임시 파일 정리
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            
            # 6. 배경음악 재개를 위해 DISCONTINUITY 태그 추가
            try:
                with open(main_playlist, "a") as f:
                    f.write("\n#EXT-X-DISCONTINUITY\n")
                logger.info("🎬 Added DISCONTINUITY tag for background music resume.")
            except Exception as e:
                logger.error(f"❌ Failed to write DISCONTINUITY tag: {e}")

            # 7. 배경음악 스트림 재개
            logger.info("▶️  Resuming background stream after commentary (club %s)", club_id)
            audio_file_path = self.audio_files.get(club_id)
            if audio_file_path:
                try:
                    # --- 재생 재개 위치 계산 ---
                    import time
                    start_time = self.stream_start_times.get(club_id)
                    resume_pos_seconds = 0
                    if start_time:
                        total_duration = self._get_audio_duration(audio_file_path)
                        if total_duration > 0:
                            elapsed_time = time.time() - start_time
                            resume_pos_seconds = elapsed_time % total_duration
                            logger.info("🎵 Resuming audio from %.2f seconds (total: %.2f, elapsed: %.2f)", 
                                      resume_pos_seconds, total_duration, elapsed_time)
                        else:
                            logger.warning("⚠️ Cannot get audio duration, starting from beginning")
                    # --------------------------

                    # 현재 세그먼트 번호 업데이트
                    current_segment_num = self._get_current_segment_number(club_id)
                    if current_segment_num is not None:
                        self.segment_counters[club_id] = current_segment_num + 1
                        logger.info("🔢 Next segment number: %d (club %s)", self.segment_counters[club_id], club_id)

                    # 무한 반복을 보장하기 위해 filter_complex 사용
                    restart_command = [
                        "ffmpeg",
                        "-re",
                        "-ss", str(resume_pos_seconds),  # 시작 위치
                        "-i", audio_file_path,
                        "-filter_complex", f"[0:a]aloop=loop=-1:size=2e+09[looped]",  # 무한 반복 필터
                        "-map", "[looped]",
                        "-c:a", "aac", "-b:a", "128k",
                        "-f", "hls",
                        "-hls_time", "4",
                        "-hls_list_size", "10",  # 지연 시간 단축
                        "-hls_flags", "delete_segments+append_list+program_date_time+split_by_time",
                        "-start_number", str(self.segment_counters[club_id]),
                        "-hls_segment_filename", os.path.join(stream_dir, "segment_%03d.ts"),
                        main_playlist,
                    ]
                    
                    logger.info("🔧 Starting new FFmpeg process with command: %s", ' '.join(restart_command))
                    new_proc = await asyncio.create_subprocess_exec(*restart_command,
                                                                    stdout=asyncio.subprocess.PIPE,
                                                                    stderr=asyncio.subprocess.PIPE)
                    self.processes[club_id] = new_proc
                    
                    # 새 프로세스의 시작 시간 기준을 재설정
                    self.stream_start_times[club_id] = time.time() - resume_pos_seconds
                    logger.info("✅ Background stream resumed successfully (club %s)", club_id)
                    
                    # 프로세스 상태 확인 (비동기로)
                    asyncio.create_task(self._monitor_process(club_id, new_proc, "background_music_resume"))
                    
                except Exception as e:
                    logger.error("❌ Failed to resume background stream (club %s): %s", club_id, e)
                    # 실패 시 기본 스트림 재시작 시도
                    try:
                        logger.info("🔄 Attempting fallback stream restart (club %s)", club_id)
                        await self.start_stream(club_id, audio_file_path)
                    except Exception as fallback_error:
                        logger.error("❌ Fallback stream restart also failed (club %s): %s", club_id, fallback_error)


    # ------------------------------------------------------------------
    async def resume_background_music(self, club_id: int, audio_file_path: str, start_position: float = 0.0):
        """배경음악을 특정 위치부터 이어서 재생하도록 새로운 ffmpeg 파이프를 붙인다."""
        await self.stop_stream(club_id)
        # 재시작
        await self.start_stream(club_id, audio_file_path)

    # ------------------------------------------------------------------
    def _stream_dir(self, club_id: int) -> str:
        return os.path.join(self.base_dir, f"club_{club_id}")

    def _playlist_url(self, club_id: int) -> str:
        # NOTE: adjust host externally if needed
        return f"/static/hls/radio/club_{club_id}/playlist.m3u8"
    
    async def _cleanup_segments(self, club_id: int):
        """세그먼트 파일 정리 (선택적)"""
        try:
            stream_dir = self._stream_dir(club_id)

            if os.path.exists(stream_dir):
                import glob
                # .ts 파일들 삭제
                ts_files = glob.glob(os.path.join(stream_dir, "*.ts"))
                for ts_file in ts_files:
                    try:
                        os.unlink(ts_file)
                    except OSError:
                        pass
                
                # playlist.m3u8 은 남겨두어 late joiners 가 404 를 보지 않음
                logger.info("🧹 club %s 세그먼트 파일 정리 완료 (playlist 유지)", club_id)
        except Exception as e:
            logger.error("세그먼트 정리 오류 (club %s): %s", club_id, e)

    async def _monitor_process(self, club_id: int, process, process_name: str):
        """FFmpeg 프로세스 상태를 모니터링하고 오류 시 로깅"""
        try:
            stdout, stderr = await process.communicate()
            
            # SIGTERM(15)으로 종료된 경우 return code는 143이 됨. 이는 정상 종료로 간주.
            # 255는 가끔 non-graceful terminate 시 발생할 수 있으므로 이것도 정상으로 처리.
            if process.returncode not in [0, 143, 255]:
                logger.error(f"❌ FFmpeg process '{process_name}' failed (club {club_id}) with return code {process.returncode}")
                if stderr:
                    logger.error(f"❌ FFmpeg stderr (club {club_id}): {stderr.decode()}")
                self.processes.pop(club_id, None)
            else:
                log_message = f"ℹ️ FFmpeg process '{process_name}' completed (club {club_id}) with code {process.returncode}"
                if process.returncode in [143, 255]:
                    log_message += " (Terminated as expected)"
                logger.info(log_message)
        except Exception as e:
            logger.error(f"❌ Error monitoring FFmpeg process '{process_name}' (club {club_id}): %s", e)

    def _get_current_segment_number(self, club_id: int) -> int | None:
        """현재 플레이리스트에서 마지막 세그먼트 번호를 가져옴"""
        try:
            playlist_path = os.path.join(self._stream_dir(club_id), "playlist.m3u8")
            if not os.path.exists(playlist_path):
                return None
                
            with open(playlist_path, 'r') as f:
                lines = f.readlines()
            
            # 마지막 .ts 파일에서 번호 추출
            for line in reversed(lines):
                line = line.strip()
                if line.endswith('.ts'):
                    # segment_12345.ts -> 12345
                    try:
                        segment_num = int(line.split('_')[1].split('.')[0])
                        return segment_num
                    except (IndexError, ValueError):
                        continue
            
            return None
        except Exception as e:
            logger.error("현재 세그먼트 번호 가져오기 실패 (club %s): %s", club_id, e)
            return None

    def _get_audio_duration(self, file_path: str) -> float:
        """ffprobe를 사용하여 오디오 파일의 길이를 초 단위로 반환 (동기 함수)"""
        import subprocess
        try:
            probe_cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", file_path
            ]
            result = subprocess.check_output(probe_cmd, text=True).strip()
            return float(result)
        except Exception as e:
            logger.error("Failed to get duration for %s: %s", file_path, e)
            return 0.0

# singleton
hls_service = HLSService()
"""
