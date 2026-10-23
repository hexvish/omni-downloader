package com.hexvish.omnidownloader.util

import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMuxer
import java.io.File
import java.nio.ByteBuffer

object MediaMuxerHelper {

    @JvmStatic
    fun mux(videoPath: String, audioPath: String, outputPath: String): Boolean {
        val videoFile = File(videoPath)
        val audioFile = File(audioPath)
        val outputFile = File(outputPath)

        if (!videoFile.exists() || !audioFile.exists()) return false

        var videoExtractor: MediaExtractor? = null
        var audioExtractor: MediaExtractor? = null
        var muxer: MediaMuxer? = null

        try {
            videoExtractor = MediaExtractor().apply { setDataSource(videoFile.absolutePath) }
            audioExtractor = MediaExtractor().apply { setDataSource(audioFile.absolutePath) }

            // Ensure output directory exists and target file is clean
            outputFile.parentFile?.mkdirs()
            if (outputFile.exists()) {
                outputFile.delete()
            }

            muxer = MediaMuxer(outputFile.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)

            var videoTrackIndex = -1
            for (i in 0 until videoExtractor.trackCount) {
                val format = videoExtractor.getTrackFormat(i)
                val mime = format.getString(MediaFormat.KEY_MIME) ?: ""
                if (mime.startsWith("video/")) {
                    videoTrackIndex = muxer.addTrack(format)
                    videoExtractor.selectTrack(i)
                    break
                }
            }

            var audioTrackIndex = -1
            for (i in 0 until audioExtractor.trackCount) {
                val format = audioExtractor.getTrackFormat(i)
                val mime = format.getString(MediaFormat.KEY_MIME) ?: ""
                if (mime.startsWith("audio/")) {
                    audioTrackIndex = muxer.addTrack(format)
                    audioExtractor.selectTrack(i)
                    break
                }
            }

            if (videoTrackIndex < 0 || audioTrackIndex < 0) {
                return false
            }

            muxer.start()

            val bufferSize = 2 * 1024 * 1024 // 2 MB buffer
            val buffer = ByteBuffer.allocate(bufferSize)
            val bufferInfo = MediaCodec.BufferInfo()

            var firstVideoTimeUs = -1L
            var firstAudioTimeUs = -1L
            var lastVideoTimeUs = 0L
            var lastAudioTimeUs = 0L

            var videoDone = false
            var audioDone = false

            // Interleaved sample writing based on presentation timestamp
            while (!videoDone || !audioDone) {
                val videoTime = if (!videoDone) videoExtractor.sampleTime else Long.MAX_VALUE
                val audioTime = if (!audioDone) audioExtractor.sampleTime else Long.MAX_VALUE

                if (!videoDone && (audioDone || videoTime <= audioTime)) {
                    bufferInfo.offset = 0
                    val readSize = videoExtractor.readSampleData(buffer, 0)
                    if (readSize < 0) {
                        videoDone = true
                    } else {
                        bufferInfo.size = readSize
                        val sampleTime = videoExtractor.sampleTime
                        if (firstVideoTimeUs < 0) firstVideoTimeUs = sampleTime
                        val adjusted = Math.max(lastVideoTimeUs, sampleTime - firstVideoTimeUs)
                        lastVideoTimeUs = adjusted

                        bufferInfo.presentationTimeUs = adjusted
                        bufferInfo.flags = videoExtractor.sampleFlags
                        muxer.writeSampleData(videoTrackIndex, buffer, bufferInfo)
                        videoExtractor.advance()
                    }
                } else if (!audioDone) {
                    bufferInfo.offset = 0
                    val readSize = audioExtractor.readSampleData(buffer, 0)
                    if (readSize < 0) {
                        audioDone = true
                    } else {
                        bufferInfo.size = readSize
                        val sampleTime = audioExtractor.sampleTime
                        if (firstAudioTimeUs < 0) firstAudioTimeUs = sampleTime
                        val adjusted = Math.max(lastAudioTimeUs, sampleTime - firstAudioTimeUs)
                        lastAudioTimeUs = adjusted

                        bufferInfo.presentationTimeUs = adjusted
                        bufferInfo.flags = audioExtractor.sampleFlags
                        muxer.writeSampleData(audioTrackIndex, buffer, bufferInfo)
                        audioExtractor.advance()
                    }
                }
            }

            muxer.stop()
            return outputFile.exists() && outputFile.length() > 0
        } catch (e: Exception) {
            e.printStackTrace()
            return false
        } finally {
            try { videoExtractor?.release() } catch (_: Exception) {}
            try { audioExtractor?.release() } catch (_: Exception) {}
            try { muxer?.release() } catch (_: Exception) {}
        }
    }
}
