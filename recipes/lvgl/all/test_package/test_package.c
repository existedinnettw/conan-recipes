#include <lvgl/lvgl.h>
#if LV_BUILD_DEMOS
#include <lvgl/demos/lv_demos.h>
#endif

#include <stdio.h>

#define HOR_RES 320
#define VER_RES 240

static uint8_t draw_buf[HOR_RES * VER_RES / 10 * 4];
static int flushes;

static void flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map)
{
    (void)area;
    (void)px_map;
    flushes++;
    lv_display_flush_ready(disp);
}

int main(int argc, char **argv)
{
    (void)argv;
    lv_init();

    /* The backends need a real display or input device, so only check that
     * they link; argc is never this large in the test run. */
    if (argc > 99) {
#if LV_USE_SDL
        lv_sdl_window_create(HOR_RES, VER_RES);
#endif
#if LV_USE_LINUX_FBDEV
        lv_linux_fbdev_create();
#endif
#if LV_USE_LINUX_DRM
        lv_linux_drm_create();
#endif
#if LV_USE_WAYLAND
        lv_wayland_window_create(HOR_RES, VER_RES, "test_package", NULL);
#endif
#if LV_USE_EVDEV
        lv_evdev_create(LV_INDEV_TYPE_POINTER, "/dev/input/event0");
#endif
    }

    lv_display_t *disp = lv_display_create(HOR_RES, VER_RES);
    lv_display_set_flush_cb(disp, flush_cb);
    lv_display_set_buffers(disp, draw_buf, NULL, sizeof(draw_buf), LV_DISPLAY_RENDER_MODE_PARTIAL);

#if LV_USE_DEMO_WIDGETS
    lv_demo_widgets();
#else
    lv_obj_t *label = lv_label_create(lv_screen_active());
    lv_label_set_text(label, "Hello, LVGL");
    lv_obj_center(label);
#endif

    for (int i = 0; i < 10; i++) {
        lv_tick_inc(5);
        lv_timer_handler();
    }

    printf("LVGL %d.%d.%d rendered %d flushes\n",
           lv_version_major(), lv_version_minor(), lv_version_patch(), flushes);
    lv_deinit();
    return flushes > 0 ? 0 : 1;
}
