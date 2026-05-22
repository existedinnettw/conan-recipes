#include <linux/init.h>
#include <linux/module.h>

static int __init test_kbuild_module_init(void)
{
    return 0;
}

static void __exit test_kbuild_module_exit(void)
{
}

module_init(test_kbuild_module_init);
module_exit(test_kbuild_module_exit);

MODULE_DESCRIPTION("linux-kbuild-tree Conan test module");
MODULE_LICENSE("GPL");
