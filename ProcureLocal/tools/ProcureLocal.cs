using System;
using System.IO;
using System.Diagnostics;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Collections.Generic;

[assembly: System.Reflection.AssemblyTitle("ProcureLocal Enterprise Studio")]
[assembly: System.Reflection.AssemblyDescription("Enterprise Procurement, Comparative Statements, Centralized Storage & Polyglot Engine")]
[assembly: System.Reflection.AssemblyCompany("ProcureLocal Enterprise")]
[assembly: System.Reflection.AssemblyProduct("ProcureLocal Desktop")]
[assembly: System.Reflection.AssemblyVersion("3.5.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("3.5.0.0")]

namespace ProcureLocalApp
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            string baseDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');

            // 1. Resolve Server Script & Working Directory
            string serverJs = null;
            string workingDir = null;

            string[] candidateScripts = new string[] {
                Path.Combine(baseDir, "server.js"),
                Path.Combine(baseDir, "ProcureLocal", "server.js"),
                Path.Combine(baseDir, "core", "server.js"),
                Path.Combine(baseDir, "app", "server.js")
            };

            foreach (string cs in candidateScripts)
            {
                if (File.Exists(cs))
                {
                    serverJs = cs;
                    workingDir = Path.GetDirectoryName(cs);
                    break;
                }
            }

            // 2. Resolve Host Configuration
            int defaultPort = 3002;
            string configJson = ResolveConfigFile(baseDir);
            if (!string.IsNullOrEmpty(configJson) && File.Exists(configJson))
            {
                try
                {
                    string txt = File.ReadAllText(configJson);
                    Match m = Regex.Match(txt, @"""port""\s*:\s*(\d+)");
                    if (m.Success) defaultPort = int.Parse(m.Groups[1].Value);
                }
                catch { }
            }

            // 3. Command Line Argument Processing
            if (args.Length > 0)
            {
                string cmd = args[0].ToLowerInvariant();
                if (cmd == "--stop" || cmd == "-stop" || cmd == "/stop")
                {
                    StopServer("http://127.0.0.1:" + defaultPort);
                    return;
                }
                if (cmd == "--shortcut" || cmd == "-shortcut")
                {
                    CreateDesktopShortcut(baseDir);
                    return;
                }
                if (cmd == "--python" || cmd == "-python")
                {
                    RunPythonModule(baseDir, args);
                    return;
                }
                if (cmd == "--java" || cmd == "-java")
                {
                    RunJavaModule(baseDir, args);
                    return;
                }
                if (cmd == "--print-raw" || cmd == "-print-raw")
                {
                    if (args.Length >= 3)
                    {
                        RawPrinterHelper.SendStringToPrinter(args[1], args[2]);
                    }
                    return;
                }
            }

            // Try creating desktop shortcut silently
            try { CreateDesktopShortcut(baseDir); } catch { }

            // 4. Standalone Mode Resolution (1-Step Direct Execution)
            // Central Database & Document Vault path is stored in config.json under "dataDir": "\\\\Server\\ProcureDB"
            string configFile = ResolveConfigFile(baseDir);
            if (string.IsNullOrEmpty(configFile))
            {
                configFile = Path.Combine(baseDir, "config.json");
            }

            // Command-line flag to configure remote database share: ProcureLocal.exe --set-db "\\server\share\ProcureDB"
            if (args.Length >= 2 && (args[0].ToLowerInvariant() == "--set-db" || args[0].ToLowerInvariant() == "--remotedb"))
            {
                string remotePath = args[1].Trim();
                try
                {
                    string curText = File.Exists(configFile) ? File.ReadAllText(configFile) : "{}";
                    string curBak = "";
                    Match mb = Regex.Match(curText, @"""remoteBackupDir""\s*:\s*""([^""]+)""");
                    if (mb.Success) curBak = mb.Groups[1].Value.Replace("\\\\", "\\");

                    string outCfg = "{\r\n  \"dataDir\": \"" + remotePath.Replace("\\", "\\\\") + "\",\r\n" + (string.IsNullOrEmpty(curBak) ? "" : "  \"remoteBackupDir\": \"" + curBak.Replace("\\", "\\\\") + "\",\r\n") + "  \"port\": " + defaultPort + "\r\n}\r\n";
                    File.WriteAllText(configFile, outCfg);
                    MessageBox.Show("Remote Shared Database configured successfully to:\n" + remotePath + "\n\nAll workstations will store and access central data in this remote location.", "ProcureLocal Remote DB", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show("Failed to save remote DB configuration: " + ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
                return;
            }

            // Command-line flag to configure remote backup share: ProcureLocal.exe --set-backup "\\server\share\Backups"
            if (args.Length >= 2 && (args[0].ToLowerInvariant() == "--set-backup" || args[0].ToLowerInvariant() == "--remotebackup"))
            {
                string remoteBak = args[1].Trim();
                try
                {
                    string curText = File.Exists(configFile) ? File.ReadAllText(configFile) : "{}";
                    string dataDir = "./DB";
                    Match md = Regex.Match(curText, @"""dataDir""\s*:\s*""([^""]+)""");
                    if (md.Success) dataDir = md.Groups[1].Value.Replace("\\\\", "\\");

                    string outCfg = "{\r\n  \"dataDir\": \"" + dataDir.Replace("\\", "\\\\") + "\",\r\n  \"remoteBackupDir\": \"" + remoteBak.Replace("\\", "\\\\") + "\",\r\n  \"port\": " + defaultPort + "\r\n}\r\n";
                    File.WriteAllText(configFile, outCfg);
                    MessageBox.Show("Remote Backup Destination configured successfully to:\n" + remoteBak + "\n\nAll database backups and document snapshots will mirror to this location automatically.", "ProcureLocal Remote Backup", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show("Failed to save remote backup configuration: " + ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                }
                return;
            }

            // Optional explicit setup dialog only if requested via --setup or --config-db
            bool forceSetup = (args.Length > 0 && (args[0].ToLowerInvariant() == "--setup" || args[0].ToLowerInvariant() == "--config-db"));
            if (forceSetup)
            {
                using (RemoteDbConfigForm dbDlg = new RemoteDbConfigForm(configFile))
                {
                    if (dbDlg.ShowDialog() != DialogResult.OK)
                    {
                        return; // User cancelled
                    }
                }
            }

            // 5. Standalone 1-Step Execution: Always launch local engine (attached to configured remote DB) and open UI
            string targetUrl = "http://127.0.0.1:" + defaultPort;
            if (!IsServerOnline(targetUrl))
            {
                if (string.IsNullOrEmpty(serverJs) || !File.Exists(serverJs))
                {
                    MessageBox.Show(
                        "Core server engine (server.js) could not be located in this folder.",
                        "ProcureLocal Error",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                string nodeExe = ResolveNodePath(baseDir);
                if (string.IsNullOrEmpty(nodeExe))
                {
                    MessageBox.Show(
                        "Node.js runtime was not detected on this system.\nPlease ensure Node.js is installed or node.exe is present in the core directory.",
                        "ProcureLocal Error",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = nodeExe;
                psi.Arguments = "\"" + serverJs + "\"";
                psi.WorkingDirectory = workingDir;
                psi.CreateNoWindow = true;
                psi.UseShellExecute = false;
                psi.WindowStyle = ProcessWindowStyle.Hidden;

                Process srvProc = null;
                try
                {
                    srvProc = Process.Start(psi);
                }
                catch (Exception ex)
                {
                    MessageBox.Show(
                        "Failed to initialize ProcureLocal background service:\n" + ex.Message,
                        "ProcureLocal Launch Error",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                // Poll /api/health until server is online (up to 15s)
                bool isReady = false;
                for (int i = 0; i < 30; i++)
                {
                    Thread.Sleep(500);
                    if (IsServerOnline(targetUrl))
                    {
                        isReady = true;
                        break;
                    }
                    if (srvProc != null && srvProc.HasExited)
                    {
                        MessageBox.Show(
                            "The ProcureLocal engine terminated unexpectedly with exit code: " + srvProc.ExitCode,
                            "ProcureLocal Engine Error",
                            MessageBoxButtons.OK,
                            MessageBoxIcon.Error
                        );
                        return;
                    }
                }

                if (!isReady)
                {
                    MessageBox.Show(
                        "Engine startup timed out on " + targetUrl + ".\nPlease verify port availability or network share permissions.",
                        "ProcureLocal Warning",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Warning
                    );
                }
            }

            // 6. Launch Desktop Application Window
            LaunchDesktopApp(targetUrl);
        }

        public static bool IsServerOnline(string baseUrl)
        {
            try
            {
                string url = baseUrl.TrimEnd('/') + "/api/health";
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(url);
                req.Timeout = 1800;
                req.Method = "GET";
                using (HttpWebResponse res = (HttpWebResponse)req.GetResponse())
                {
                    return res.StatusCode == HttpStatusCode.OK;
                }
            }
            catch
            {
                return false;
            }
        }

        private static void StopServer(string baseUrl)
        {
            try
            {
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(baseUrl.TrimEnd('/') + "/api/shutdown");
                req.Timeout = 2000;
                req.Method = "POST";
                using (req.GetResponse()) { }
            }
            catch { }
        }

        private static string ResolveConfigFile(string baseDir)
        {
            string[] candidateConfigs = new string[] {
                Path.Combine(baseDir, "config.json"),
                Path.Combine(baseDir, "ProcureLocal", "config.json"),
                Path.Combine(baseDir, "tools", "config.json"),
                Path.Combine(baseDir, "ProcureLocal", "tools", "config.json")
            };
            foreach (string cfg in candidateConfigs)
            {
                if (File.Exists(cfg)) return cfg;
            }
            return null;
        }

        private static string ResolveNodePath(string baseDir)
        {
            string[] localPaths = new string[] {
                Path.Combine(baseDir, "core", "node.exe"),
                Path.Combine(baseDir, "ProcureLocal", "core", "node.exe"),
                Path.Combine(baseDir, "app", "node.exe"),
                Path.Combine(baseDir, "node.exe")
            };
            foreach (string p in localPaths)
            {
                if (File.Exists(p)) return p;
            }

            string pf64 = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "nodejs", "node.exe");
            if (File.Exists(pf64)) return pf64;

            string pf86 = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "nodejs", "node.exe");
            if (File.Exists(pf86)) return pf86;

            return "node.exe";
        }

        private static void LaunchDesktopApp(string appUrl)
        {
            string[] candidateEdge = new string[] {
                @"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                @"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Microsoft\Edge\Application\msedge.exe")
            };

            string edgePath = null;
            foreach (string ep in candidateEdge)
            {
                if (File.Exists(ep)) { edgePath = ep; break; }
            }

            string userProfile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "ProcureLocal", "AppProfile");
            try { Directory.CreateDirectory(userProfile); } catch { }

            if (!string.IsNullOrEmpty(edgePath))
            {
                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = edgePath;
                psi.Arguments = "--app=\"" + appUrl + "\" --user-data-dir=\"" + userProfile + "\" --no-first-run --no-default-browser-check";
                psi.UseShellExecute = true;
                Process.Start(psi);
            }
            else
            {
                Process.Start(appUrl);
            }
        }

        private static void RunPythonModule(string baseDir, string[] args)
        {
            string script = args.Length > 1 ? args[1] : "spend_analytics.py";
            string pyDir = Path.Combine(baseDir, "python");
            if (!Directory.Exists(pyDir)) pyDir = Path.Combine(baseDir, "ProcureLocal", "python");

            string fullScript = Path.Combine(pyDir, script);
            if (!File.Exists(fullScript)) fullScript = script;

            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = "python";
            psi.Arguments = "\"" + fullScript + "\"";
            psi.WorkingDirectory = Directory.Exists(pyDir) ? pyDir : baseDir;
            psi.UseShellExecute = false;

            try
            {
                Process p = Process.Start(psi);
                p.WaitForExit();
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to launch Python engine: " + ex.Message, "Python Suite Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private static void RunJavaModule(string baseDir, string[] args)
        {
            string javaDir = Path.Combine(baseDir, "java");
            if (!Directory.Exists(javaDir)) javaDir = Path.Combine(baseDir, "ProcureLocal", "java");

            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = "java";
            psi.Arguments = "-cp . com.procurelocal.ProcureSapBridge";
            psi.WorkingDirectory = Directory.Exists(javaDir) ? javaDir : baseDir;
            psi.UseShellExecute = false;

            try
            {
                Process p = Process.Start(psi);
                p.WaitForExit();
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to launch Java Enterprise SAP Bridge: " + ex.Message, "Java Suite Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private static void CreateDesktopShortcut(string baseDir)
        {
            try
            {
                string userProfile = Environment.GetEnvironmentVariable("USERPROFILE");
                string desktopDir = !string.IsNullOrEmpty(userProfile) ? Path.Combine(userProfile, "Desktop") : Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                if (string.IsNullOrEmpty(desktopDir) || !Directory.Exists(desktopDir)) return;

                string shortcutPath = Path.Combine(desktopDir, "ProcureLocal.lnk");
                string targetExe = Path.Combine(baseDir, "ProcureLocal.exe");
                if (!File.Exists(targetExe)) targetExe = Path.Combine(baseDir, "ProcureLocal", "ProcureLocal.exe");
                string iconPath = Path.Combine(Path.GetDirectoryName(targetExe), "ProcureLocal.ico");

                if (!File.Exists(targetExe)) return;

                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                if (shellType == null) return;
                dynamic shell = Activator.CreateInstance(shellType);
                dynamic shortcut = shell.CreateShortcut(shortcutPath);
                shortcut.TargetPath = targetExe;
                shortcut.WorkingDirectory = Path.GetDirectoryName(targetExe);
                shortcut.Description = "ProcureLocal Enterprise Procurement Studio";
                if (File.Exists(iconPath))
                {
                    shortcut.IconLocation = iconPath + ",0";
                }
                shortcut.Save();
            }
            catch { }
        }
    }

    // -------------------------------------------------------------------------
    // Remote Network Shared Database Configuration Form (NAS / Windows Share)
    // -------------------------------------------------------------------------
    public class RemoteDbConfigForm : Form
    {
        private string configPath;
        private TextBox txtRemotePath;
        private Button btnBrowse;
        private Button btnTest;
        private Label lblStatus;
        private Button btnSave;
        private Button btnCancel;

        public RemoteDbConfigForm(string configPath)
        {
            this.configPath = configPath;
            InitializeComponent();
            LoadCurrentConfig();
        }

        private void InitializeComponent()
        {
            this.Text = "ProcureLocal – Remote Network Shared Database Configuration";
            this.Width = 620;
            this.Height = 360;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.BackColor = Color.White;
            this.Font = new Font("Segoe UI", 9.5f, FontStyle.Regular);

            Panel pnlBanner = new Panel();
            pnlBanner.Dock = DockStyle.Top;
            pnlBanner.Height = 70;
            pnlBanner.BackColor = Color.FromArgb(248, 250, 252);
            pnlBanner.Paint += (s, e) => {
                e.Graphics.DrawLine(new Pen(Color.FromArgb(226, 232, 240)), 0, 69, pnlBanner.Width, 69);
            };

            Label lblTitle = new Label();
            lblTitle.Text = "📁 Remote Shared Database (NAS / Windows Share)";
            lblTitle.Font = new Font("Segoe UI", 12f, FontStyle.Bold);
            lblTitle.ForeColor = Color.FromArgb(15, 23, 42);
            lblTitle.Location = new Point(18, 12);
            lblTitle.AutoSize = true;
            pnlBanner.Controls.Add(lblTitle);

            Label lblSubtitle = new Label();
            lblSubtitle.Text = "All workstations store and access central procure.db & document vault at this remote path.";
            lblSubtitle.ForeColor = Color.FromArgb(100, 116, 139);
            lblSubtitle.Location = new Point(20, 38);
            lblSubtitle.AutoSize = true;
            pnlBanner.Controls.Add(lblSubtitle);

            this.Controls.Add(pnlBanner);

            Label lblPath = new Label();
            lblPath.Text = "Remote Database Network Folder / UNC Path (or Mapped Drive):";
            lblPath.Font = new Font("Segoe UI", 9.5f, FontStyle.Bold);
            lblPath.Location = new Point(24, 88);
            lblPath.AutoSize = true;
            this.Controls.Add(lblPath);

            txtRemotePath = new TextBox();
            txtRemotePath.Location = new Point(24, 114);
            txtRemotePath.Width = 450;
            txtRemotePath.Font = new Font("Consolas", 10f);
            this.Controls.Add(txtRemotePath);

            btnBrowse = new Button();
            btnBrowse.Text = "Browse...";
            btnBrowse.Location = new Point(484, 112);
            btnBrowse.Width = 105;
            btnBrowse.Height = 28;
            btnBrowse.Click += (s, e) => BrowseFolder();
            this.Controls.Add(btnBrowse);

            Label lblHint = new Label();
            lblHint.Text = "Examples:\n  • Windows UNC Share: \\\\192.168.1.100\\SharedData\\ProcureDB\n  • Mapped Drive: Z:\\ProcureDB\n  • Local Standalone: ./DB";
            lblHint.ForeColor = Color.FromArgb(100, 116, 139);
            lblHint.Font = new Font("Segoe UI", 8.5f);
            lblHint.Location = new Point(24, 148);
            lblHint.Width = 560;
            lblHint.Height = 55;
            this.Controls.Add(lblHint);

            btnTest = new Button();
            btnTest.Text = "🔄 Test Read/Write Access";
            btnTest.Location = new Point(24, 212);
            btnTest.Width = 200;
            btnTest.Height = 30;
            btnTest.Click += (s, e) => TestStorageAccess();
            this.Controls.Add(btnTest);

            lblStatus = new Label();
            lblStatus.Location = new Point(234, 218);
            lblStatus.Width = 350;
            lblStatus.Height = 24;
            lblStatus.Text = "";
            this.Controls.Add(lblStatus);

            Panel pnlBottom = new Panel();
            pnlBottom.Dock = DockStyle.Bottom;
            pnlBottom.Height = 55;
            pnlBottom.BackColor = Color.FromArgb(241, 245, 249);

            btnSave = new Button();
            btnSave.Text = "💾 Save Remote Path & Launch";
            btnSave.Width = 240;
            btnSave.Height = 34;
            btnSave.Location = new Point(345, 10);
            btnSave.BackColor = Color.FromArgb(37, 99, 235);
            btnSave.ForeColor = Color.White;
            btnSave.FlatStyle = FlatStyle.Flat;
            btnSave.FlatAppearance.BorderSize = 0;
            btnSave.Font = new Font("Segoe UI", 9.5f, FontStyle.Bold);
            btnSave.Click += (s, e) => SaveAndClose();
            pnlBottom.Controls.Add(btnSave);

            btnCancel = new Button();
            btnCancel.Text = "Cancel";
            btnCancel.Width = 85;
            btnCancel.Height = 34;
            btnCancel.Location = new Point(250, 10);
            btnCancel.Click += (s, e) => { this.DialogResult = DialogResult.Cancel; this.Close(); };
            pnlBottom.Controls.Add(btnCancel);

            this.Controls.Add(pnlBottom);
        }

        private void LoadCurrentConfig()
        {
            try
            {
                if (File.Exists(configPath))
                {
                    string json = File.ReadAllText(configPath);
                    Match m = Regex.Match(json, @"""dataDir""\s*:\s*""([^""]+)""");
                    if (m.Success)
                    {
                        txtRemotePath.Text = m.Groups[1].Value.Replace("\\\\", "\\");
                    }
                }
            }
            catch { }
            if (string.IsNullOrEmpty(txtRemotePath.Text))
            {
                txtRemotePath.Text = @"\\Server\SharedData\ProcureDB";
            }
        }

        private void BrowseFolder()
        {
            using (FolderBrowserDialog fbd = new FolderBrowserDialog())
            {
                fbd.Description = "Select Remote Network Shared Folder or Mapped Drive for Central Database";
                if (fbd.ShowDialog() == DialogResult.OK)
                {
                    txtRemotePath.Text = fbd.SelectedPath;
                }
            }
        }

        private void TestStorageAccess()
        {
            string p = txtRemotePath.Text.Trim();
            if (string.IsNullOrEmpty(p))
            {
                lblStatus.ForeColor = Color.FromArgb(185, 28, 28);
                lblStatus.Text = "Please enter a valid remote path.";
                return;
            }
            lblStatus.ForeColor = Color.FromArgb(37, 99, 235);
            lblStatus.Text = "Testing access...";
            lblStatus.Refresh();
            try
            {
                Directory.CreateDirectory(p);
                string testFile = Path.Combine(p, ".procure_test_" + Guid.NewGuid().ToString("N"));
                File.WriteAllText(testFile, "test");
                File.Delete(testFile);
                lblStatus.ForeColor = Color.FromArgb(22, 101, 52);
                lblStatus.Text = "✅ Access OK: Network share is writable!";
            }
            catch (Exception ex)
            {
                lblStatus.ForeColor = Color.FromArgb(185, 28, 28);
                lblStatus.Text = "❌ Error: " + ex.Message;
            }
        }

        private void SaveAndClose()
        {
            string p = txtRemotePath.Text.Trim();
            if (string.IsNullOrEmpty(p))
            {
                MessageBox.Show("Please specify a valid path.", "Validation", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            try
            {
                string outJson = "{\r\n  \"dataDir\": \"" + p.Replace("\\", "\\\\") + "\",\r\n  \"port\": 3000\r\n}\r\n";
                File.WriteAllText(configPath, outJson);
                this.DialogResult = DialogResult.OK;
                this.Close();
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to save config: " + ex.Message, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }

    // -------------------------------------------------------------------------
    // Direct Hardware Barcode Thermal Printer Helper (Zebra / TSC / ESC-POS)
    // -------------------------------------------------------------------------
    public class RawPrinterHelper
    {
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)]
        public class DOCINFOA
        {
            [MarshalAs(UnmanagedType.LPStr)]
            public string pDocName;
            [MarshalAs(UnmanagedType.LPStr)]
            public string pOutputFile;
            [MarshalAs(UnmanagedType.LPStr)]
            public string pDataType;
        }

        [DllImport("winspool.Drv", EntryPoint = "OpenPrinterA", SetLastError = true, CharSet = CharSet.Ansi, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
        public static extern bool OpenPrinter([MarshalAs(UnmanagedType.LPStr)] string szPrinter, out IntPtr hPrinter, IntPtr pd);

        [DllImport("winspool.Drv", EntryPoint = "ClosePrinter", SetLastError = true, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
        public static extern bool ClosePrinter(IntPtr hPrinter);

        [DllImport("winspool.Drv", EntryPoint = "StartDocPrinterA", SetLastError = true, CharSet = CharSet.Ansi, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
        public static extern bool StartDocPrinter(IntPtr hPrinter, int level, [In, MarshalAs(UnmanagedType.LPStruct)] DOCINFOA di);

        [DllImport("winspool.Drv", EntryPoint = "EndDocPrinter", SetLastError = true, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
        public static extern bool EndDocPrinter(IntPtr hPrinter);

        [DllImport("winspool.Drv", EntryPoint = "StartPagePrinter", SetLastError = true, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
        public static extern bool StartPagePrinter(IntPtr hPrinter);

        [DllImport("winspool.Drv", EntryPoint = "EndPagePrinter", SetLastError = true, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
        public static extern bool EndPagePrinter(IntPtr hPrinter);

        [DllImport("winspool.Drv", EntryPoint = "WritePrinter", SetLastError = true, ExactSpelling = true, CallingConvention = CallingConvention.StdCall)]
        public static extern bool WritePrinter(IntPtr hPrinter, IntPtr pBytes, int dwCount, out int dwWritten);

        public static bool SendBytesToPrinter(string szPrinterName, IntPtr pBytes, int dwCount)
        {
            IntPtr hPrinter = IntPtr.Zero;
            DOCINFOA di = new DOCINFOA();
            bool bSuccess = false;

            di.pDocName = "ProcureLocal Asset Barcode";
            di.pDataType = "RAW";

            if (OpenPrinter(szPrinterName.Normalize(), out hPrinter, IntPtr.Zero))
            {
                if (StartDocPrinter(hPrinter, 1, di))
                {
                    if (StartPagePrinter(hPrinter))
                    {
                        int dwWritten = 0;
                        bSuccess = WritePrinter(hPrinter, pBytes, dwCount, out dwWritten);
                        EndPagePrinter(hPrinter);
                    }
                    EndDocPrinter(hPrinter);
                }
                ClosePrinter(hPrinter);
            }
            return bSuccess;
        }

        public static bool SendStringToPrinter(string szPrinterName, string szString)
        {
            IntPtr pBytes = Marshal.StringToCoTaskMemAnsi(szString);
            int dwCount = szString.Length;
            bool bSuccess = SendBytesToPrinter(szPrinterName, pBytes, dwCount);
            Marshal.FreeCoTaskMem(pBytes);
            return bSuccess;
        }
    }
}
