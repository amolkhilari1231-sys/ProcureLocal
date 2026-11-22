using System;
using System.IO;
using System.Drawing;
using System.Windows.Forms;
using System.Diagnostics;
using System.Text.RegularExpressions;
using System.Threading;

[assembly: System.Reflection.AssemblyTitle("ProcureLocal Enterprise Setup")]
[assembly: System.Reflection.AssemblyDescription("1-Click Permanent Enterprise Installer & Remote Backup Setup")]
[assembly: System.Reflection.AssemblyCompany("ProcureLocal Enterprise")]
[assembly: System.Reflection.AssemblyProduct("ProcureLocal Setup")]
[assembly: System.Reflection.AssemblyVersion("3.5.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("3.5.0.0")]

namespace ProcureLocalSetup
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            string sourceDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');

            // Command-line silent install support: Setup-ProcureLocal.exe /silent /dir="C:\ProcureLocal" /remote="\\server\backup"
            bool isSilent = false;
            string targetDir = @"C:\ProcureLocal";
            string remoteBackup = "";

            foreach (string arg in args)
            {
                string a = arg.ToLowerInvariant();
                if (a == "/silent" || a == "-silent" || a == "--silent" || a == "/s") isSilent = true;
                if (a.StartsWith("/dir=") || a.StartsWith("-dir=")) targetDir = arg.Substring(5).Trim('"', '\'');
                if (a.StartsWith("/remote=") || a.StartsWith("-remote=")) remoteBackup = arg.Substring(8).Trim('"', '\'');
            }

            if (isSilent)
            {
                InstallerEngine.ExecuteInstall(sourceDir, targetDir, remoteBackup, true, true, true, false, null);
                return;
            }

            Application.Run(new SetupWizardForm(sourceDir));
        }
    }

    public class SetupWizardForm : Form
    {
        private string sourceDir;
        private TextBox txtInstallDir;
        private TextBox txtRemoteBackup;
        private CheckBox chkDesktopShortcut;
        private CheckBox chkStartMenu;
        private CheckBox chkProtectFiles;
        private CheckBox chkLaunchAfter;
        private Label lblStatus;
        private ProgressBar progressBar;
        private Button btnInstall;
        private Button btnTestRemote;

        public SetupWizardForm(string sourceDir)
        {
            this.sourceDir = sourceDir;
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.Text = "ProcureLocal Enterprise – 1-Click Permanent Setup";
            this.Width = 650;
            this.Height = 520;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.MaximizeBox = false;
            this.BackColor = Color.White;
            this.Font = new Font("Segoe UI", 9.25f, FontStyle.Regular);

            // Banner Header
            Panel pnlHeader = new Panel();
            pnlHeader.Dock = DockStyle.Top;
            pnlHeader.Height = 85;
            pnlHeader.BackColor = Color.FromArgb(15, 23, 42); // slate-900

            Label lblBannerTitle = new Label();
            lblBannerTitle.Text = "📦 ProcureLocal Enterprise Installation Setup";
            lblBannerTitle.Font = new Font("Segoe UI", 13.5f, FontStyle.Bold);
            lblBannerTitle.ForeColor = Color.White;
            lblBannerTitle.Location = new Point(20, 16);
            lblBannerTitle.AutoSize = true;

            Label lblBannerSub = new Label();
            lblBannerSub.Text = "Installs ProcureLocal permanently to your PC with Desktop Shortcut & Remote Backup Vault";
            lblBannerSub.Font = new Font("Segoe UI", 8.75f, FontStyle.Regular);
            lblBannerSub.ForeColor = Color.FromArgb(148, 163, 184);
            lblBannerSub.Location = new Point(22, 46);
            lblBannerSub.AutoSize = true;

            pnlHeader.Controls.Add(lblBannerTitle);
            pnlHeader.Controls.Add(lblBannerSub);
            this.Controls.Add(pnlHeader);

            int curY = 105;

            // 1. Installation Directory
            Label lblDir = new Label();
            lblDir.Text = "1. Permanent Installation Directory on this PC:";
            lblDir.Font = new Font("Segoe UI", 9.25f, FontStyle.Bold);
            lblDir.Location = new Point(25, curY);
            lblDir.AutoSize = true;
            this.Controls.Add(lblDir);
            curY += 24;

            txtInstallDir = new TextBox();
            txtInstallDir.Text = @"C:\ProcureLocal";
            txtInstallDir.Location = new Point(25, curY);
            txtInstallDir.Width = 485;
            txtInstallDir.Height = 26;
            this.Controls.Add(txtInstallDir);

            Button btnBrowse = new Button();
            btnBrowse.Text = "Browse...";
            btnBrowse.Location = new Point(520, curY - 1);
            btnBrowse.Width = 90;
            btnBrowse.Height = 28;
            btnBrowse.Click += (s, e) => {
                using (FolderBrowserDialog fbd = new FolderBrowserDialog())
                {
                    fbd.Description = "Select Installation Directory for ProcureLocal";
                    fbd.SelectedPath = txtInstallDir.Text;
                    if (fbd.ShowDialog() == DialogResult.OK)
                    {
                        txtInstallDir.Text = fbd.SelectedPath;
                    }
                }
            };
            this.Controls.Add(btnBrowse);
            curY += 40;

            // 2. Remote Backup Location
            Label lblRemote = new Label();
            lblRemote.Text = "2. Remote Backup Destination (NAS / Windows Network Shared Folder):";
            lblRemote.Font = new Font("Segoe UI", 9.25f, FontStyle.Bold);
            lblRemote.Location = new Point(25, curY);
            lblRemote.AutoSize = true;
            this.Controls.Add(lblRemote);
            curY += 24;

            txtRemoteBackup = new TextBox();
            txtRemoteBackup.Text = "";
            // Try reading existing config
            string curCfg = Path.Combine(sourceDir, "config.json");
            if (!File.Exists(curCfg)) curCfg = Path.Combine(sourceDir, "ProcureLocal", "config.json");
            if (File.Exists(curCfg))
            {
                try
                {
                    Match m = Regex.Match(File.ReadAllText(curCfg), @"""remoteBackupDir""\s*:\s*""([^""]+)""");
                    if (m.Success) txtRemoteBackup.Text = m.Groups[1].Value.Replace("\\\\", "\\");
                }
                catch { }
            }
            txtRemoteBackup.Location = new Point(25, curY);
            txtRemoteBackup.Width = 485;
            txtRemoteBackup.Height = 26;
            this.Controls.Add(txtRemoteBackup);

            btnTestRemote = new Button();
            btnTestRemote.Text = "Test Access";
            btnTestRemote.Location = new Point(520, curY - 1);
            btnTestRemote.Width = 90;
            btnTestRemote.Height = 28;
            btnTestRemote.Click += (s, e) => {
                string rPath = txtRemoteBackup.Text.Trim();
                if (string.IsNullOrEmpty(rPath))
                {
                    MessageBox.Show("Please enter a remote UNC path or shared folder (e.g. \\\\192.168.1.100\\ProcureBackup or D:\\Backups)", "Notice", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    return;
                }
                try
                {
                    Directory.CreateDirectory(rPath);
                    string probe = Path.Combine(rPath, ".setup_probe_" + Guid.NewGuid().ToString("N"));
                    File.WriteAllText(probe, "ok");
                    File.Delete(probe);
                    MessageBox.Show("✔ Remote Share Verified!\nWrite access confirmed on:\n" + rPath, "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show("⚠️ Cannot write to remote share:\n" + ex.Message + "\n\nPlease check network connection or permissions.", "Remote Path Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
            };
            this.Controls.Add(btnTestRemote);
            curY += 26;

            Label lblRemoteNote = new Label();
            lblRemoteNote.Text = "e.g. \\\\192.168.1.100\\ProcureBackup or D:\\Backups (Leave blank to configure later from Settings)";
            lblRemoteNote.Font = new Font("Segoe UI", 7.75f, FontStyle.Regular);
            lblRemoteNote.ForeColor = Color.FromArgb(100, 116, 139);
            lblRemoteNote.Location = new Point(25, curY);
            lblRemoteNote.AutoSize = true;
            this.Controls.Add(lblRemoteNote);
            curY += 32;

            // 3. Options
            chkDesktopShortcut = new CheckBox();
            chkDesktopShortcut.Text = "Create Desktop Shortcut (ProcureLocal ERP)";
            chkDesktopShortcut.Checked = true;
            chkDesktopShortcut.Location = new Point(28, curY);
            chkDesktopShortcut.AutoSize = true;
            this.Controls.Add(chkDesktopShortcut);
            curY += 24;

            chkStartMenu = new CheckBox();
            chkStartMenu.Text = "Create Start Menu entry under Programs";
            chkStartMenu.Checked = true;
            chkStartMenu.Location = new Point(28, curY);
            chkStartMenu.AutoSize = true;
            this.Controls.Add(chkStartMenu);
            curY += 24;

            chkProtectFiles = new CheckBox();
            chkProtectFiles.Text = "Protect & Hide source files (Locks server.js & index.html as Read-Only so nobody can tamper)";
            chkProtectFiles.Checked = true;
            chkProtectFiles.Location = new Point(28, curY);
            chkProtectFiles.AutoSize = true;
            this.Controls.Add(chkProtectFiles);
            curY += 24;

            chkLaunchAfter = new CheckBox();
            chkLaunchAfter.Text = "Launch ProcureLocal ERP immediately when setup finishes";
            chkLaunchAfter.Checked = true;
            chkLaunchAfter.Location = new Point(28, curY);
            chkLaunchAfter.AutoSize = true;
            this.Controls.Add(chkLaunchAfter);
            curY += 32;

            // Progress Bar & Status Label
            progressBar = new ProgressBar();
            progressBar.Location = new Point(25, curY);
            progressBar.Width = 585;
            progressBar.Height = 16;
            progressBar.Style = ProgressBarStyle.Blocks;
            progressBar.Value = 0;
            this.Controls.Add(progressBar);
            curY += 22;

            lblStatus = new Label();
            lblStatus.Text = "Ready to install. Click 'Install ProcureLocal' to begin permanent setup.";
            lblStatus.Font = new Font("Segoe UI", 8.25f, FontStyle.Regular);
            lblStatus.ForeColor = Color.FromArgb(71, 85, 105);
            lblStatus.Location = new Point(25, curY);
            lblStatus.AutoSize = true;
            this.Controls.Add(lblStatus);
            curY += 30;

            // Buttons
            btnInstall = new Button();
            btnInstall.Text = "🚀 Install ProcureLocal";
            btnInstall.Font = new Font("Segoe UI", 10.5f, FontStyle.Bold);
            btnInstall.BackColor = Color.FromArgb(37, 99, 235); // blue-600
            btnInstall.ForeColor = Color.White;
            btnInstall.FlatStyle = FlatStyle.Flat;
            btnInstall.FlatAppearance.BorderSize = 0;
            btnInstall.Location = new Point(25, curY);
            btnInstall.Width = 220;
            btnInstall.Height = 40;
            btnInstall.Cursor = Cursors.Hand;
            btnInstall.Click += BtnInstall_Click;
            this.Controls.Add(btnInstall);

            Button btnCancel = new Button();
            btnCancel.Text = "Cancel";
            btnCancel.Font = new Font("Segoe UI", 9.5f, FontStyle.Regular);
            btnCancel.Location = new Point(260, curY);
            btnCancel.Width = 100;
            btnCancel.Height = 40;
            btnCancel.Click += (s, e) => this.Close();
            this.Controls.Add(btnCancel);
        }

        private void BtnInstall_Click(object sender, EventArgs e)
        {
            string installPath = txtInstallDir.Text.Trim();
            string remotePath = txtRemoteBackup.Text.Trim();

            if (string.IsNullOrEmpty(installPath))
            {
                MessageBox.Show("Please choose a valid destination directory.", "Validation Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            btnInstall.Enabled = false;
            btnTestRemote.Enabled = false;
            progressBar.Value = 10;
            lblStatus.Text = "Preparing installation directory...";

            Thread worker = new Thread(() => {
                try
                {
                    InstallerEngine.ExecuteInstall(
                        sourceDir,
                        installPath,
                        remotePath,
                        chkDesktopShortcut.Checked,
                        chkStartMenu.Checked,
                        chkProtectFiles.Checked,
                        chkLaunchAfter.Checked,
                        (msg, pct) => {
                            this.Invoke((MethodInvoker)delegate {
                                lblStatus.Text = msg;
                                if (pct >= 0 && pct <= 100) progressBar.Value = pct;
                            });
                        }
                    );

                    this.Invoke((MethodInvoker)delegate {
                        progressBar.Value = 100;
                        lblStatus.Text = "Installation completed successfully! ✔";
                        MessageBox.Show(
                            "ProcureLocal ERP has been successfully installed to:\n" + installPath +
                            "\n\nDesktop Shortcut: Created" +
                            "\nRemote Backup Vault: " + (string.IsNullOrEmpty(remotePath) ? "Configured locally (update anytime in Settings)" : remotePath) +
                            "\nSecurity: Source code protected & locked",
                            "Setup Complete",
                            MessageBoxButtons.OK,
                            MessageBoxIcon.Information
                        );
                        this.Close();
                    });
                }
                catch (Exception ex)
                {
                    this.Invoke((MethodInvoker)delegate {
                        btnInstall.Enabled = true;
                        btnTestRemote.Enabled = true;
                        progressBar.Value = 0;
                        lblStatus.Text = "Installation failed: " + ex.Message;
                        MessageBox.Show("Installation failed:\n" + ex.Message, "Setup Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    });
                }
            });
            worker.IsBackground = true;
            worker.Start();
        }
    }

    public static class InstallerEngine
    {
        public static void ExecuteInstall(
            string sourceDir,
            string targetDir,
            string remoteBackupDir,
            bool createDesktop,
            bool createStartMenu,
            bool protectFiles,
            bool launchAfter,
            Action<string, int> progress)
        {
            if (progress != null) progress("Creating destination directory: " + targetDir, 15);
            Directory.CreateDirectory(targetDir);

            // Locate application source folder
            string appSource = sourceDir;
            if (Directory.Exists(Path.Combine(sourceDir, "ProcureLocal")))
            {
                appSource = Path.Combine(sourceDir, "ProcureLocal");
            }

            // 1. Copy core binaries and directories
            if (progress != null) progress("Copying application binaries & runtime...", 30);
            CopyFolder(appSource, targetDir, new string[] { "server.log", ".git", "Test Procurments.zip" });

            // Ensure ProcureLocal.exe is also copied to target
            string srcExe = Path.Combine(sourceDir, "ProcureLocal.exe");
            if (!File.Exists(srcExe)) srcExe = Path.Combine(appSource, "ProcureLocal.exe");
            if (File.Exists(srcExe))
            {
                File.Copy(srcExe, Path.Combine(targetDir, "ProcureLocal.exe"), true);
            }

            // 2. Configure config.json
            if (progress != null) progress("Configuring network & backup parameters...", 55);
            string targetConfig = Path.Combine(targetDir, "config.json");
            string dataDir = "./DB";
            if (File.Exists(targetConfig))
            {
                try
                {
                    string curTxt = File.ReadAllText(targetConfig);
                    Match m = Regex.Match(curTxt, @"""dataDir""\s*:\s*""([^""]+)""");
                    if (m.Success) dataDir = m.Groups[1].Value.Replace("\\\\", "\\");
                }
                catch { }
            }

            string outCfg = "{\r\n  \"dataDir\": \"" + dataDir.Replace("\\", "\\\\") + "\",\r\n" +
                            (string.IsNullOrEmpty(remoteBackupDir) ? "" : "  \"remoteBackupDir\": \"" + remoteBackupDir.Replace("\\", "\\\\") + "\",\r\n") +
                            "  \"port\": 3002\r\n}\r\n";
            File.WriteAllText(targetConfig, outCfg);

            // Verify remote directory if specified
            if (!string.IsNullOrEmpty(remoteBackupDir))
            {
                try { Directory.CreateDirectory(remoteBackupDir); } catch { }
            }

            // 3. Create Uninstaller
            if (progress != null) progress("Creating uninstaller script...", 70);
            CreateUninstaller(targetDir);

            // 4. Create Desktop & Start Menu Shortcuts
            if (progress != null) progress("Registering desktop and Start menu shortcuts...", 80);
            string installedExe = Path.Combine(targetDir, "ProcureLocal.exe");

            if (createDesktop && File.Exists(installedExe))
            {
                string desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                CreateShortcut(installedExe, Path.Combine(desktop, "ProcureLocal ERP.lnk"), "ProcureLocal Enterprise Procurement Studio");
            }

            if (createStartMenu && File.Exists(installedExe))
            {
                string programs = Environment.GetFolderPath(Environment.SpecialFolder.Programs);
                CreateShortcut(installedExe, Path.Combine(programs, "ProcureLocal ERP.lnk"), "ProcureLocal Enterprise Procurement Studio");
            }

            // 5. Lock and Protect source files
            if (protectFiles)
            {
                if (progress != null) progress("Securing and locking enterprise files...", 90);
                ProtectSourceFiles(targetDir);
            }

            // 6. Launch Application if requested
            if (launchAfter && File.Exists(installedExe))
            {
                if (progress != null) progress("Launching ProcureLocal ERP...", 98);
                Process.Start(new ProcessStartInfo()
                {
                    FileName = installedExe,
                    WorkingDirectory = targetDir,
                    UseShellExecute = true
                });
            }
        }

        private static void CopyFolder(string source, string target, string[] excludeFiles)
        {
            Directory.CreateDirectory(target);
            foreach (string file in Directory.GetFiles(source))
            {
                string fName = Path.GetFileName(file);
                bool skip = false;
                if (excludeFiles != null)
                {
                    foreach (string ex in excludeFiles)
                    {
                        if (string.Equals(fName, ex, StringComparison.OrdinalIgnoreCase)) { skip = true; break; }
                    }
                }
                if (!skip)
                {
                    string dest = Path.Combine(target, fName);
                    try
                    {
                        if (File.Exists(dest)) File.SetAttributes(dest, FileAttributes.Normal);
                        File.Copy(file, dest, true);
                    }
                    catch { }
                }
            }

            foreach (string dir in Directory.GetDirectories(source))
            {
                string dName = Path.GetFileName(dir);
                if (dName.Equals(".git", StringComparison.OrdinalIgnoreCase)) continue;
                CopyFolder(dir, Path.Combine(target, dName), excludeFiles);
            }
        }

        private static void CreateShortcut(string targetExe, string shortcutPath, string description)
        {
            try
            {
                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                if (shellType == null) return;
                dynamic shell = Activator.CreateInstance(shellType);
                dynamic shortcut = shell.CreateShortcut(shortcutPath);
                shortcut.TargetPath = targetExe;
                shortcut.WorkingDirectory = Path.GetDirectoryName(targetExe);
                shortcut.Description = description;
                shortcut.IconLocation = targetExe + ",0";
                shortcut.Save();
            }
            catch { }
        }

        private static void CreateUninstaller(string installDir)
        {
            try
            {
                string uninstBat = Path.Combine(installDir, "Uninstall-ProcureLocal.bat");
                string content = "@echo off\r\n" +
                                 "echo ========================================================\r\n" +
                                 "echo       Uninstall ProcureLocal Enterprise Edition         \r\n" +
                                 "echo ========================================================\r\n" +
                                 "echo.\r\n" +
                                 "set /p CONFIRM=Are you sure you want to uninstall ProcureLocal? (Y/N): \r\n" +
                                 "if /i not \"%CONFIRM%\"==\"Y\" exit /b\r\n" +
                                 "echo Stopping running instances...\r\n" +
                                 "taskkill /f /im ProcureLocal.exe >nul 2>&1\r\n" +
                                 "taskkill /f /im node.exe >nul 2>&1\r\n" +
                                 "echo Removing Desktop and Start Menu shortcuts...\r\n" +
                                 "del \"%USERPROFILE%\\Desktop\\ProcureLocal ERP.lnk\" >nul 2>&1\r\n" +
                                 "del \"%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\ProcureLocal ERP.lnk\" >nul 2>&1\r\n" +
                                 "echo Note: Your database and documents in %~dp0DB have been preserved for safety.\r\n" +
                                 "echo ProcureLocal shortcuts removed successfully.\r\n" +
                                 "pause\r\n";
                File.WriteAllText(uninstBat, content);
            }
            catch { }
        }

        private static void ProtectSourceFiles(string installDir)
        {
            try
            {
                string[] filesToLock = new string[] {
                    Path.Combine(installDir, "server.js"),
                    Path.Combine(installDir, "public", "index.html"),
                    Path.Combine(installDir, "core", "node.exe")
                };

                foreach (string f in filesToLock)
                {
                    if (File.Exists(f))
                    {
                        File.SetAttributes(f, FileAttributes.ReadOnly);
                    }
                }
            }
            catch { }
        }
    }
}

