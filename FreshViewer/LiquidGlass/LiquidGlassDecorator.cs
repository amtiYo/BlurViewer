using Avalonia;
using Avalonia.Controls;
using Avalonia.Media;
using Avalonia.Media.Imaging;
using Avalonia.Platform;
using Avalonia.Rendering;
using Avalonia.Rendering.SceneGraph;
using Avalonia.Skia;
using Avalonia.VisualTree;
using SkiaSharp;
using System;
using System.IO;

namespace FreshViewer.UI.LiquidGlass
{
    // 注意：此控件现在应用的是“液态玻璃”扭曲效果，而不是之前的毛玻璃模糊。
    public class LiquidGlassDecorator : Decorator
    {
        #region Re-entrancy Guard

        // 一个防止 Render 方法被递归调用的标志。
        private bool _isRendering;

        #endregion

        #region Avalonia Properties

        public static readonly StyledProperty<double> RadiusProperty =
            AvaloniaProperty.Register<LiquidGlassDecorator, double>(nameof(Radius), 25.0);

        // Radius 属性现在控制扭曲效果。
        public double Radius
        {
            get => GetValue(RadiusProperty);
            set => SetValue(RadiusProperty, value);
        }

        #endregion

        static LiquidGlassDecorator()
        {
            // 当 Radius 属性变化时，触发重绘。
            AffectsRender<LiquidGlassDecorator>(RadiusProperty);
        }

        /// <summary>
        /// 重写标准的 Render 方法来执行所有绘制操作。
        /// </summary>
        public override void Render(DrawingContext context)
        {
            // 重入守卫：如果我们已经在渲染中，则不开始新的渲染。
            // 这会打破递归循环。
            if (_isRendering)
                return;

            try
            {
                _isRendering = true;

                // ВАЖНО: сначала рисуем эффект стекла по снимку уже отрисованного фона,
                // затем поверх — дочерний контент. Иначе непрозрачный шейдер перекрывает UI.
                if (LiquidGlassPlatform.SupportsAdvancedEffects)
                {
                    // Поверх детей накладываем жидкостный шейдер.
                    context.Custom(new LiquidGlassDrawOperation(new Rect(0, 0, Bounds.Width, Bounds.Height), this));
                }
                else
                {
                    // Если шейдеры недоступны — рисуем прозрачное стекло поверх.
                    DrawFallbackOverlay(context);
                }

                // Теперь выводим дочерние элементы поверх стекла
                base.Render(context);
            }
            finally
            {
                _isRendering = false;
            }
        }

        private void DrawFallbackOverlay(DrawingContext context)
        {
            var bounds = new Rect(0, 0, Bounds.Width, Bounds.Height);
            if (bounds.Width <= 0 || bounds.Height <= 0)
            {
                return;
            }

            var rounded = new RoundedRect(bounds, new CornerRadius(Radius));

            var backdrop = new LinearGradientBrush
            {
                StartPoint = new RelativePoint(0.05, 0.0, RelativeUnit.Relative),
                EndPoint = new RelativePoint(0.95, 1.0, RelativeUnit.Relative),
                GradientStops = new GradientStops
                {
                    new GradientStop(Color.FromArgb(0xF5, 0xFF, 0xFF, 0xFF), 0),
                    new GradientStop(Color.FromArgb(0xE2, 0xF3, 0xFF, 0xFF), 0.5),
                    new GradientStop(Color.FromArgb(0xCC, 0xE6, 0xF5, 0xFF), 1)
                }
            };

            context.DrawRectangle(backdrop, null, rounded);

            var topHighlight = new LinearGradientBrush
            {
                StartPoint = new RelativePoint(0, 0, RelativeUnit.Relative),
                EndPoint = new RelativePoint(0, 1, RelativeUnit.Relative),
                GradientStops = new GradientStops
                {
                    new GradientStop(Color.FromArgb(0xBE, 0xFF, 0xFF, 0xFF), 0),
                    new GradientStop(Color.FromArgb(0x25, 0xFF, 0xFF, 0xFF), 1)
                }
            };

            context.DrawRectangle(topHighlight, null,
                new RoundedRect(new Rect(bounds.X + 6, bounds.Y + 6, bounds.Width - 12, bounds.Height * 0.5),
                    new CornerRadius(Radius)));

            var bottomGlowRect = new Rect(bounds.X + 10, bounds.Bottom - Math.Min(bounds.Height * 0.5, 120),
                bounds.Width - 20, Math.Min(bounds.Height * 0.5, 120));
            var bottomGlow = new RadialGradientBrush
            {
                Center = new RelativePoint(0.5, 1.15, RelativeUnit.Relative),
                GradientOrigin = new RelativePoint(0.5, 1.15, RelativeUnit.Relative),
                RadiusX = new RelativeScalar(1.0, RelativeUnit.Relative),
                RadiusY = new RelativeScalar(1.0, RelativeUnit.Relative),
                GradientStops = new GradientStops
                {
                    new GradientStop(Color.FromArgb(0x45, 0xD6, 0xF0, 0xFF), 0),
                    new GradientStop(Color.FromArgb(0x00, 0xD6, 0xF0, 0xFF), 1)
                }
            };

            context.DrawRectangle(bottomGlow, null, new RoundedRect(bottomGlowRect, new CornerRadius(Radius)));

            var borderPen = new Pen(new SolidColorBrush(Color.FromArgb(0x5A, 0xC4, 0xD8, 0xFF)), 1.0);
            context.DrawRectangle(null, borderPen, rounded);
        }

        /// <summary>
        /// 处理 Skia 渲染的自定义绘制操作。
        /// </summary>
        private class LiquidGlassDrawOperation : ICustomDrawOperation
        {
            private readonly Rect _bounds;
            private readonly LiquidGlassDecorator _owner;

            private static SKRuntimeEffect? _effect;
            private static bool _isShaderLoaded;

            public LiquidGlassDrawOperation(Rect bounds, LiquidGlassDecorator owner)
            {
                _bounds = bounds;
                _owner = owner;
            }

            public void Dispose()
            {
            }

            public bool HitTest(Point p) => _bounds.Contains(p);

            public Rect Bounds => _bounds;

            public bool Equals(ICustomDrawOperation? other) => false;

            public void Render(ImmediateDrawingContext context)
            {
                var leaseFeature = context.TryGetFeature<ISkiaSharpApiLeaseFeature>();
                if (leaseFeature is null) return;

                LoadShader();

                using var lease = leaseFeature.Lease();
                var canvas = lease.SkCanvas;

                if (_effect is null)
                {
                    DrawErrorHint(canvas);
                }
                else
                {
                    DrawLiquidGlassEffect(canvas, lease);
                }
            }

            private void LoadShader()
            {
                if (_isShaderLoaded) return;
                _isShaderLoaded = true;

                try
                {
                    // 更新为加载新的液态玻璃着色器。
                    var assetUri = new Uri("avares://FreshViewer/LiquidGlass/Assets/Shaders/LiquidGlassShader.sksl");
                    using var stream = AssetLoader.Open(assetUri);
                    using var reader = new StreamReader(stream);
                    var shaderCode = reader.ReadToEnd();

                    _effect = SKRuntimeEffect.Create(shaderCode, out var errorText);
                    if (_effect == null)
                    {
                        Console.WriteLine($"创建 SKRuntimeEffect 失败: {errorText}");
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"加载着色器时发生异常: {ex.Message}");
                }
            }

            private void DrawErrorHint(SKCanvas canvas)
            {
                using var errorPaint = new SKPaint
                {
                    Color = new SKColor(255, 0, 0, 120), // 半透明红色
                    Style = SKPaintStyle.Fill
                };
                canvas.DrawRect(SKRect.Create(0, 0, (float)_bounds.Width, (float)_bounds.Height), errorPaint);

                using var textPaint = new SKPaint
                {
                    Color = SKColors.White,
                    TextSize = 14,
                    IsAntialias = true,
                    TextAlign = SKTextAlign.Center
                };
                canvas.DrawText("着色器加载失败！", (float)_bounds.Width / 2, (float)_bounds.Height / 2, textPaint);
            }

            private void DrawLiquidGlassEffect(SKCanvas canvas, ISkiaSharpApiLease lease)
            {
                if (_effect is null) return;

                var pixelWidth = (int)Math.Ceiling(_bounds.Width);
                var pixelHeight = (int)Math.Ceiling(_bounds.Height);
                if (pixelWidth <= 0 || pixelHeight <= 0) return;

                using var snapshot = lease.SkSurface?.Snapshot();
                if (snapshot is null) return;

                if (!canvas.TotalMatrix.TryInvert(out var inverse))
                {
                    return;
                }

                using var shaderImage = snapshot.ToShader(SKShaderTileMode.Clamp, SKShaderTileMode.Clamp, inverse);

                var uniforms = new SKRuntimeEffectUniforms(_effect)
                {
                    ["radius"] = (float)_owner.Radius,
                    ["resolution"] = new[] { (float)pixelWidth, (float)pixelHeight }
                };

                var children = new SKRuntimeEffectChildren(_effect) { { "content", shaderImage } };
                using var finalShader = _effect.ToShader(false, uniforms, children);

                using var paint = new SKPaint { Shader = finalShader };
                canvas.DrawRect(SKRect.Create(0, 0, pixelWidth, pixelHeight), paint);
            }
        }
    }
}
