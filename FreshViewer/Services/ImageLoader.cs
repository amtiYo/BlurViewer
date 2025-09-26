using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using System.Runtime.InteropServices;
using Avalonia;
using Avalonia.Media.Imaging;
using Avalonia.Platform;
using FreshViewer.Models;
using ImageMagick;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.Formats.Gif;
using SixLabors.ImageSharp.Formats.Png;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Processing;

namespace FreshViewer.Services;

public sealed class ImageLoader
{
    private static readonly HashSet<string> AnimatedExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".gif", ".apng", ".mng"
    };

    private static readonly HashSet<string> RawExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef", ".srw",
        ".x3f", ".mrw", ".dcr", ".kdc", ".erf", ".mef", ".mos", ".ptx", ".r3d", ".fff", ".iiq"
    };

    private static readonly HashSet<string> MagickStaticExtensions = new(StringComparer.OrdinalIgnoreCase)
    {
        ".avif", ".heic", ".heif", ".psd", ".tga", ".svg", ".webp", ".hdr", ".exr", ".j2k", ".jp2", ".jpf"
    };

    public async Task<LoadedImage> LoadAsync(string path, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            throw new ArgumentException("Path is required", nameof(path));
        }

        var extension = Path.GetExtension(path);
        if (RawExtensions.Contains(extension))
        {
            try
            {
                return await Task.Run(() => LoadRawInternal(path, cancellationToken), cancellationToken).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                throw;
            }
            catch (MagickException)
            {
                // fallback to default pipeline
            }
        }

        if (AnimatedExtensions.Contains(extension))
        {
            return await Task.Run(() => LoadAnimatedInternal(path, cancellationToken), cancellationToken).ConfigureAwait(false);
        }

        var preferMagick = MagickStaticExtensions.Contains(extension);

        if (preferMagick)
        {
            try
            {
                return await Task.Run(() => LoadStaticWithMagick(path, cancellationToken), cancellationToken).ConfigureAwait(false);
            }
            catch (Exception) when (!cancellationToken.IsCancellationRequested)
            {
                // fallback below
            }
        }

        return await Task.Run(() => LoadStaticInternal(path, extension, cancellationToken), cancellationToken).ConfigureAwait(false);
    }

    private static LoadedImage LoadStaticInternal(string path, string extension, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        try
        {
            using var stream = File.OpenRead(path);
            var bitmap = new Bitmap(stream);
            var metadata = MetadataBuilder.Build(path, bitmap.PixelSize, false, bitmap, null);
            return new LoadedImage(path, bitmap, null, metadata);
        }
        catch (Exception) when (!cancellationToken.IsCancellationRequested)
        {
            if (!MagickStaticExtensions.Contains(extension))
            {
                throw;
            }

            return LoadStaticWithMagick(path, cancellationToken);
        }
    }

    private static LoadedImage LoadAnimatedInternal(string path, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        using var image = Image.Load<Rgba32>(path);

        var frames = new List<AnimatedFrame>(image.Frames.Count);
        for (var i = 0; i < image.Frames.Count; i++)
        {
            var frame = image.Frames[i];
            cancellationToken.ThrowIfCancellationRequested();

            var frameMetadata = frame.Metadata.GetGifMetadata();
            var frameDelay = frameMetadata?.FrameDelay ?? 10;
            if (frameDelay <= 1)
            {
                frameDelay = 10;
            }

            using var clone = image.Frames.CloneFrame(i);
            using var memoryStream = new MemoryStream();
            clone.Metadata.ExifProfile?.RemoveValue(SixLabors.ImageSharp.Metadata.Profiles.Exif.ExifTag.Orientation);
            clone.Save(memoryStream, new PngEncoder());
            memoryStream.Position = 0;

            var backingStream = new MemoryStream(memoryStream.ToArray());
            var bitmap = new Bitmap(backingStream);
            frames.Add(new AnimatedFrame(bitmap, backingStream, TimeSpan.FromMilliseconds(frameDelay * 10)));
        }

        var gifMetadata = image.Metadata.GetGifMetadata();
        var loopCount = gifMetadata?.RepeatCount ?? 0;
        var animated = new AnimatedImage(frames, loopCount);
        Bitmap? sampleFrame = frames.Count > 0 ? frames[0].Bitmap : null;
        var builtMetadata = MetadataBuilder.Build(path, animated.PixelSize, true, sampleFrame, animated);
        return new LoadedImage(path, null, animated, builtMetadata);
    }

    private static LoadedImage LoadRawInternal(string path, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();

        var settings = new MagickReadSettings
        {
            ColorSpace = ColorSpace.sRGB,
            Depth = 8
        };

        using var magickImage = new MagickImage(path, settings);
        cancellationToken.ThrowIfCancellationRequested();

        magickImage.AutoOrient();
        magickImage.ColorSpace = ColorSpace.sRGB;
        magickImage.Depth = 8;
        return ConvertMagickImage(path, magickImage, cancellationToken);
    }

    private static LoadedImage LoadStaticWithMagick(string path, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();

        using var magickImage = new MagickImage(path);
        cancellationToken.ThrowIfCancellationRequested();

        magickImage.AutoOrient();
        magickImage.ColorSpace = ColorSpace.sRGB;
        magickImage.Depth = 8;

        return ConvertMagickImage(path, magickImage, cancellationToken);
    }

    private static LoadedImage ConvertMagickImage(string path, MagickImage magickImage, CancellationToken cancellationToken)
    {
        var width = (int)magickImage.Width;
        var height = (int)magickImage.Height;
        var pixelBytes = magickImage.ToByteArray(MagickFormat.Bgra);

        var pixelSize = new PixelSize(width, height);
        var density = magickImage.Density;
        var dpi = density.X > 0 && density.Y > 0
            ? new Vector(density.X, density.Y)
            : new Vector(96, 96);

        var writeable = new WriteableBitmap(pixelSize, dpi, PixelFormat.Bgra8888, AlphaFormat.Premul);
        using (var frame = writeable.Lock())
        {
            var stride = frame.RowBytes;
            var sourceStride = width * 4;

            for (var y = 0; y < height; y++)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var destRow = IntPtr.Add(frame.Address, y * stride);
                Marshal.Copy(pixelBytes, y * sourceStride, destRow, sourceStride);
            }
        }

        var metadata = MetadataBuilder.Build(path, writeable.PixelSize, false, writeable, null);
        return new LoadedImage(path, writeable, null, metadata);
    }
}

public sealed class LoadedImage : IDisposable
{
    public LoadedImage(string path, Bitmap? bitmap, AnimatedImage? animated, ImageMetadata? metadata)
    {
        Path = path;
        Bitmap = bitmap;
        Animation = animated;
        Metadata = metadata;
    }

    public string Path { get; }

    public Bitmap? Bitmap { get; }

    public AnimatedImage? Animation { get; }

    public ImageMetadata? Metadata { get; }

    public bool IsAnimated => Animation is not null;

    public PixelSize PixelSize
        => Animation?.PixelSize ?? Bitmap?.PixelSize ?? PixelSize.Empty;

    public void Dispose()
    {
        Bitmap?.Dispose();
        Animation?.Dispose();
    }
}

public sealed class AnimatedImage : IDisposable
{
    public AnimatedImage(IReadOnlyList<AnimatedFrame> frames, int loopCount)
    {
        Frames = frames;
        LoopCount = loopCount;
        PixelSize = frames.Count > 0 ? frames[0].Bitmap.PixelSize : PixelSize.Empty;
    }

    public IReadOnlyList<AnimatedFrame> Frames { get; }

    public int LoopCount { get; }

    public PixelSize PixelSize { get; }

    public void Dispose()
    {
        foreach (var frame in Frames)
        {
            frame.Dispose();
        }
    }
}

public sealed class AnimatedFrame : IDisposable
{
    public AnimatedFrame(Bitmap bitmap, MemoryStream backingStream, TimeSpan duration)
    {
        Bitmap = bitmap;
        BackingStream = backingStream;
        Duration = duration;
    }

    public Bitmap Bitmap { get; }

    private MemoryStream BackingStream { get; }

    public TimeSpan Duration { get; }

    public void Dispose()
    {
        Bitmap.Dispose();
        BackingStream.Dispose();
    }
}
