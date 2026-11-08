package com.ruoyi.web.controller.equipment;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Serializes capacity checks and writes within this application instance. */
@Component
public class PrivatePhotoStorage {
    private final Path directory;
    private final long maxBytes;
    private final long minFreeBytes;

    public PrivatePhotoStorage(@Value("${ems.private-upload-dir:./private-uploads}") String directory,
            @Value("${ems.private-upload-max-bytes:5368709120}") long maxBytes,
            @Value("${ems.private-upload-min-free-bytes:2147483648}") long minFreeBytes) {
        if (maxBytes <= 0 || minFreeBytes < 0) throw new IllegalArgumentException("Invalid private photo storage limits");
        this.directory = Path.of(directory).toAbsolutePath().normalize();
        this.maxBytes = maxBytes;
        this.minFreeBytes = minFreeBytes;
    }

    /** Returns null when the configured quota or filesystem reserve would be exceeded. */
    public synchronized Path store(String name, byte[] bytes) throws IOException {
        Files.createDirectories(directory);
        if (bytes.length > maxBytes || minFreeBytes > Long.MAX_VALUE - bytes.length || Files.getFileStore(directory).getUsableSpace() < minFreeBytes + (long) bytes.length) return null;
        long used = 0;
        try (var paths = Files.walk(directory)) {
            var iterator = paths.iterator();
            while (iterator.hasNext()) {
                Path path = iterator.next();
                if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) continue;
                long size = Files.size(path);
                if (size > maxBytes - used || bytes.length > maxBytes - used - size) return null;
                used += size;
            }
        }
        Path target = directory.resolve(name).normalize();
        if (!target.getParent().equals(directory)) throw new IllegalArgumentException("Invalid photo name");
        Files.createFile(target);
        try {
            Files.write(target, bytes, StandardOpenOption.WRITE);
            return target;
        } catch (IOException ex) {
            try { Files.deleteIfExists(target); } catch (IOException cleanup) { ex.addSuppressed(cleanup); }
            throw ex;
        }
    }
}
