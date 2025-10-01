"""Data loaders for main menu segments.

This module contains all async data loading methods and their corresponding
display methods, following the principle of separating data fetching from UI rendering.
"""

from textual import work
from textual.containers import ScrollableContainer
from textual.widgets import Label, Static, Rule

from ....config_manager import ConfigManager
from ....modules.system_info import SystemInfoModule
from ....modules.package_manager import PackageManagerDetector
from ....modules.app_installer import AppInstaller
from ....utils.logger import get_ui_logger

logger = get_ui_logger("data_loaders")


class SegmentDataLoader:
    """Handles async data loading for all segments."""

    def __init__(self, app_screen, config_manager: ConfigManager,
                 system_info_module: SystemInfoModule,
                 app_installer: AppInstaller):
        """Initialize the data loader.

        Args:
            app_screen: Reference to the main menu screen
            config_manager: Configuration manager instance
            system_info_module: System info module instance
            app_installer: App installer instance
        """
        self.screen = app_screen
        self.config_manager = config_manager
        self.system_info_module = system_info_module
        self.app_installer = app_installer
        self.modules_config = config_manager.get_modules_config()

    @work(exclusive=True, thread=True)
    async def load_system_info(self) -> None:
        """Load system information in background thread."""
        try:
            # Get system info in background thread
            all_info = self.system_info_module.get_all_info()

            # Update state on main thread
            def update_ui():
                self.screen.segment_states.finish_loading("system_info", all_info)
                if self.screen.selected_segment == "system_info":
                    self.screen.update_settings_panel()
                    self.screen.refresh()

            self.screen.app.call_from_thread(update_ui)

        except Exception as e:
            def update_error():
                self.screen.segment_states.set_error("system_info", str(e))
                if self.screen.selected_segment == "system_info":
                    self.screen.update_settings_panel()
                    self.screen.refresh()

            self.screen.app.call_from_thread(update_error)

    @work(exclusive=True, thread=True)
    async def load_homebrew_info(self) -> None:
        """Load Homebrew information in background thread."""
        try:
            homebrew_config = self.modules_config.get("homebrew")
            if homebrew_config is None:
                homebrew_config = {"enabled": True, "auto_install": False, "packages": []}
            else:
                homebrew_config = homebrew_config.settings

            def update_ui():
                self.screen.segment_states.finish_loading("homebrew", homebrew_config)
                if self.screen.selected_segment == "homebrew":
                    self.screen.update_settings_panel()
                    self.screen.refresh()

            self.screen.app.call_from_thread(update_ui)

        except Exception as e:
            def update_error():
                self.screen.segment_states.set_error("homebrew", str(e))
                if self.screen.selected_segment == "homebrew":
                    self.screen.update_settings_panel()
                    self.screen.refresh()

            self.screen.app.call_from_thread(update_error)

    @work(exclusive=True, thread=True)
    async def load_package_manager_info(self) -> None:
        """Load Package Manager information in background thread."""
        try:
            detector = PackageManagerDetector(self.config_manager)
            package_managers = detector.package_managers
            primary_pm = detector.get_primary_package_manager()

            pkg_info = {
                "package_managers": package_managers,
                "primary": primary_pm,
                "count": len(package_managers)
            }

            def update_ui():
                self.screen.segment_states.finish_loading("package_manager", pkg_info)
                if self.screen.selected_segment == "package_manager":
                    self.screen.update_settings_panel()
                    self.screen.refresh()

            self.screen.app.call_from_thread(update_ui)

        except Exception as e:
            def update_error():
                self.screen.segment_states.set_error("package_manager", str(e))
                if self.screen.selected_segment == "package_manager":
                    self.screen.update_settings_panel()
                    self.screen.refresh()

            self.screen.app.call_from_thread(update_error)


class SegmentDisplayRenderer:
    """Renders data for display in segment panels."""

    @staticmethod
    def display_system_info(container: ScrollableContainer, all_info: dict) -> None:
        """Display comprehensive system information in the container."""
        # Handle error case
        if "error" in all_info:
            container.mount(Label(f"Error loading system info: {all_info['error']}", classes="info-display"))
            return

        # System & Distribution Information
        if "distribution" in all_info:
            container.mount(Label("🖥️ System", classes="section-header"))

            dist_info = all_info["distribution"]
            if "System" in dist_info:
                container.mount(Label(f"System: {dist_info['System']}", classes="info-display"))
            if "Distribution" in dist_info:
                container.mount(Label(f"Distribution: {dist_info['Distribution']}", classes="info-display"))
            if "Machine" in dist_info:
                container.mount(Label(f"Architecture: {dist_info['Machine']}", classes="info-display"))
            if "Release" in dist_info:
                container.mount(Label(f"Kernel: {dist_info['Release']}", classes="info-display"))
            if "Distro Version" in dist_info and dist_info["Distro Version"]:
                container.mount(Label(f"Version: {dist_info['Distro Version']}", classes="info-display"))

        # CPU Information
        if "cpu" in all_info:
            container.mount(Label("", classes="info-display"))  # Spacing
            container.mount(Label("🎯 CPU", classes="section-header"))

            cpu_info = all_info["cpu"]
            if "CPU Count" in cpu_info:
                container.mount(Label(f"CPU Cores: {cpu_info['CPU Count']}", classes="info-display"))
            if "Logical CPUs" in cpu_info:
                container.mount(Label(f"Logical CPUs: {cpu_info['Logical CPUs']}", classes="info-display"))
            if "Current Usage" in cpu_info:
                container.mount(Label(f"CPU Usage: {cpu_info['Current Usage']}", classes="info-display"))
            if "CPU Frequency" in cpu_info:
                container.mount(Label(f"CPU Frequency: {cpu_info['CPU Frequency']}", classes="info-display"))
            if "Processor" in cpu_info and cpu_info["Processor"]:
                container.mount(Label(f"Processor: {cpu_info['Processor']}", classes="info-display"))

        # Memory Information
        if "memory" in all_info:
            container.mount(Label("", classes="info-display"))  # Spacing
            container.mount(Label("💾 Memory", classes="section-header"))

            memory_info = all_info["memory"]
            if "Total RAM" in memory_info:
                container.mount(Label(f"Total RAM: {memory_info['Total RAM']}", classes="info-display"))
            if "Available RAM" in memory_info:
                container.mount(Label(f"Available RAM: {memory_info['Available RAM']}", classes="info-display"))
            if "Used RAM" in memory_info:
                container.mount(Label(f"Used RAM: {memory_info['Used RAM']}", classes="info-display"))
            if "RAM Usage" in memory_info:
                container.mount(Label(f"Memory Usage: {memory_info['RAM Usage']}", classes="info-display"))
            if "Total Swap" in memory_info and memory_info["Total Swap"] != "0.0 B":
                container.mount(Label(f"Swap: {memory_info.get('Used Swap', '0')} / {memory_info['Total Swap']}", classes="info-display"))

        # Disk Information
        if "disk" in all_info:
            container.mount(Label("", classes="info-display"))  # Spacing
            container.mount(Label("💿 Storage", classes="section-header"))

            disk_info = all_info["disk"]
            for key, value in disk_info.items():
                if not value or (isinstance(value, str) and not value.strip()):
                    continue

                if "Usage" in key:
                    container.mount(Label(f"Disk Usage: {value}", classes="info-display"))
                elif "Free" in key:
                    container.mount(Label(f"Free Space: {value}", classes="info-display"))
                elif "Total" in key:
                    container.mount(Label(f"Total Space: {value}", classes="info-display"))
                elif key.startswith("Mount"):
                    container.mount(Label(f"{key}: {value}", classes="info-display"))
                elif "Available" in key:
                    container.mount(Label(f"{key}: {value}", classes="info-display"))
                elif "Partition" in key:
                    container.mount(Label(f"{key}: {value}", classes="info-display"))

        # Network Information
        if "network" in all_info:
            container.mount(Label("", classes="info-display"))  # Spacing
            container.mount(Label("🌐 Network", classes="section-header"))

            network_info = all_info["network"]
            interface_count = 0
            for key, value in network_info.items():
                if key.startswith("Interface") and "lo" not in key.lower():
                    interface_count += 1
                    if interface_count <= 3:  # Show up to 3 interfaces
                        container.mount(Label(f"{key}: {value}", classes="info-display"))

            if "Bytes Sent" in network_info:
                container.mount(Label(f"Network Sent: {network_info['Bytes Sent']}", classes="info-display"))
            if "Bytes Received" in network_info:
                container.mount(Label(f"Network Received: {network_info['Bytes Received']}", classes="info-display"))

        # Package Managers & Sources
        if "package_manager" in all_info:
            pkg_info = all_info["package_manager"]
            if pkg_info:
                container.mount(Label("", classes="info-display"))  # Spacing
                container.mount(Label("📦 Package Managers", classes="section-header"))

                for pm_name, pm_status in pkg_info.items():
                    container.mount(Label(f"  {pm_name}: {pm_status}", classes="info-display"))

    @staticmethod
    def display_homebrew_info(container: ScrollableContainer, homebrew_config: dict) -> None:
        """Display Homebrew information in the container."""
        if "error" in homebrew_config:
            container.mount(Label(f"Error loading Homebrew info: {homebrew_config['error']}", classes="info-display"))
            return

        container.mount(Label("► Status", classes="section-header"))
        status = "Enabled" if homebrew_config.get("enabled", True) else "Disabled"
        container.mount(Static(f"{status}", classes="info-value"))

        container.mount(Label("► Auto-install", classes="section-header"))
        auto_install = "Yes" if homebrew_config.get("auto_install", False) else "No"
        container.mount(Static(f"{auto_install}", classes="info-value"))

        container.mount(Label("► Packages", classes="section-header"))
        packages = homebrew_config.get("packages", [])
        if packages:
            container.mount(Static(f"{len(packages)} packages configured", classes="info-value"))
            container.mount(Rule(line_style="dashed"))
            for pkg in packages[:10]:
                container.mount(Static(f"  • {pkg}", classes="package-item"))
            if len(packages) > 10:
                container.mount(Static(f"  ... and {len(packages) - 10} more", classes="package-item"))
        else:
            container.mount(Static("No packages configured", classes="info-value"))

    @staticmethod
    def display_package_manager_info(container: ScrollableContainer, pkg_info: dict) -> None:
        """Display Package Manager information in the container."""
        if "error" in pkg_info:
            container.mount(Label(f"Error loading package manager info: {pkg_info['error']}", classes="info-display"))
            return

        container.mount(Label("📦 Detected Package Managers", classes="section-header"))
        container.mount(Static(f"Found {pkg_info.get('count', 0)} package manager(s)", classes="info-value"))

        if pkg_info.get("primary"):
            container.mount(Label("", classes="info-display"))  # Spacing
            container.mount(Label("► Primary Package Manager", classes="section-header"))
            primary = pkg_info["primary"]
            container.mount(Static(f"Name: {primary.name}", classes="info-value"))
            container.mount(Static(f"Command: {primary.command}", classes="info-value"))
            if hasattr(primary, 'current_source') and primary.current_source:
                container.mount(Static(f"Current Source: {primary.current_source}", classes="info-value"))

    @staticmethod
    def display_user_management_info(container: ScrollableContainer, user_config: dict) -> None:
        """Display User Management information in the container."""
        # Handle error case
        if "error" in user_config:
            container.mount(Label(f"Error loading User Management info: {user_config['error']}", classes="info-display"))
            return

        container.mount(Label("► User Creation", classes="section-header"))
        user_creation = "Enabled" if user_config.get("user_creation", True) else "Disabled"
        container.mount(Static(f"{user_creation}", classes="info-value"))

        container.mount(Label("► SSH Key Management", classes="section-header"))
        ssh_keys = "Enabled" if user_config.get("ssh_keys", True) else "Disabled"
        container.mount(Static(f"{ssh_keys}", classes="info-value"))

        container.mount(Label("► Sudo Access", classes="section-header"))
        sudo_access = "Configurable" if user_config.get("sudo_management", True) else "Manual"
        container.mount(Static(f"{sudo_access}", classes="info-value"))

    @staticmethod
    def display_settings_info(container: ScrollableContainer, settings_info: dict) -> None:
        """Display Settings information in the container."""
        # Handle error case
        if "error" in settings_info:
            container.mount(Label(f"Error loading Settings: {settings_info['error']}", classes="info-display"))
            return

        container.mount(Label("► Theme", classes="section-header"))
        current_theme = settings_info.get("theme", "default")
        container.mount(Static(f"{current_theme.title()}", classes="info-value"))

        container.mount(Label("► Debug Mode", classes="section-header"))
        debug_mode = "Enabled" if settings_info.get("debug", False) else "Disabled"
        container.mount(Static(f"{debug_mode}", classes="info-value"))

        container.mount(Label("► Auto-save", classes="section-header"))
        auto_save = "Enabled" if settings_info.get("auto_save", True) else "Disabled"
        container.mount(Static(f"{auto_save}", classes="info-value"))

        container.mount(Rule())
        container.mount(Label("Available Actions", classes="section-header"))
        container.mount(Static("• Change theme", classes="action-item"))
        container.mount(Static("• Export configuration", classes="action-item"))
        container.mount(Static("• Reset to defaults", classes="action-item"))

    @staticmethod
    def display_help_info(container: ScrollableContainer, help_info: dict) -> None:
        """Display Help information in the container."""
        # Handle error case
        if "error" in help_info:
            container.mount(Label(f"Error loading Help: {help_info['error']}", classes="info-display"))
            return

        container.mount(Label("► Keyboard Shortcuts", classes="section-header"))
        container.mount(Static("Q=Quit | S=Settings | ?=Help", classes="help-item"))
        container.mount(Static("H/J/K/L=Navigate | Enter=Select", classes="help-item"))
        container.mount(Static("1-5=Quick Select Segment", classes="help-item"))

        container.mount(Label("► Segments", classes="section-header"))
        container.mount(Static("System Status - View system information", classes="help-item"))
        container.mount(Static("Homebrew - Manage Homebrew packages", classes="help-item"))
        container.mount(Static("Package Manager - Configure package managers", classes="help-item"))
        container.mount(Static("User Management - Manage users and SSH keys", classes="help-item"))
        container.mount(Static("Settings - Application configuration", classes="help-item"))

        container.mount(Rule())
        container.mount(Label("Version Information", classes="section-header"))
        container.mount(Static(f"Application: {help_info['app_name']} v{help_info['app_version']}", classes="version-info"))
        container.mount(Static("Framework: Rich/Textual", classes="version-info"))